"""Compute morphometric features from a raw blastocyst image.

Why this exists
---------------
The tabular grader (``ml/artifacts/grading/tabular_extracted_v1``) beats the CNN — 0.59
cross-validated against 0.542 — but consumes 36 derived numbers rather than an
image. Rocha et al. produced those with their own pipeline, which Ovulite does
not have, so the better model could not be served on a freshly uploaded photo.
This module closes that gap.

The design decision that matters
--------------------------------
This does **not** attempt to reproduce Rocha's exact numbers. Their algorithm is
not published in reusable form, and a near-miss would be worse than useless: a
model trained on their values and fed slightly different ones produces confident
nonsense, silently.

Instead this computes features over the *same regions and concepts* the paper
describes — Hough-located expansion region, refractive ring, trophectoderm,
watershed-segmented inner cell mass, GLCM texture, grey-level statistics — and
the grader is then **retrained on these features**. Training and inference share
one pipeline, so agreement with the published values is a diagnostic, not a
requirement. ``extract_all_features.py`` reports that agreement per feature
so the relationship is measured rather than assumed: 5 of 36 features track the
published values strongly, 10 moderately, 21 weakly. Geometry and trophectoderm
texture agree well; the refractive-ring and cluster descriptors measure
something different.

Regions
-------
ER   expansion region — the whole blastocyst disc, located by Hough circle.
RR   refractive ring — the outer annulus, the zona/edge where light refracts.
TE   trophectoderm — the inner disc excluding the ICM.
ICM  inner cell mass — the dense darker mass, segmented by watershed.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

# Fractions of the detected radius. The refractive ring is the outer shell; the
# trophectoderm is everything inside it that is not ICM.
# Every image is resized to this width before measurement. Two reasons: the
# watershed step is ~8x faster, and — more importantly — size-bearing features
# (Radius ER, Sum ER, Mean Count) become comparable across inputs. Rocha's set
# is uniformly 1280x1024; a photo from a lab microscope will not be, and
# without this the same embryo would score differently by camera.
WORKING_WIDTH = 640

RR_INNER_FRACTION = 0.82
GLCM_LEVELS = 32
GLCM_DISTANCE = 3

FEATURE_NAMES = [
    # Expansion region
    "Radius ER", "Sum ER", "Mean grey ER",
    # Refractive ring: texture then grey-level statistics
    "Contrast RR", "Correlation RR", "Energy RR", "Homogeneity RR",
    "Deviation RR", "Mean grey RR", "Mode value RR", "Dark RR", "Bright RR", "Mean Count RR",
    # Trophectoderm
    "Contrast TE", "Correlation TE", "Energy TE", "Homogeneity TE",
    "Deviation TE", "Mean grey TE", "Mode grey TE", "Dark TE", "Bright TE", "Mean Count TE",
    # Inner cell mass
    "Area ICM", "Convex ICM", "Eccen ICM", "Mean ICM",
    # Dark/light cluster descriptors and watershed count
    "DC1", "Mean DC1", "LC1", "Mean LC1", "DC2", "Mean DC2", "LC2", "Mean LC2", "WSN",
]


class BlastocystNotFound(RuntimeError):
    """Raised when no plausible blastocyst disc can be located."""


def locate_blastocyst(grey: np.ndarray) -> tuple[int, int, int]:
    """Find the blastocyst disc: Hough circle, falling back to Otsu contours.

    Hough is what the paper describes and it is reliable on this framing (one
    centred embryo, consistent magnification). The fallback exists because a
    single failed detection should degrade to a worse estimate, not an
    exception, when this runs over a user's upload.
    """
    h, w = grey.shape
    blur = cv2.GaussianBlur(grey, (9, 9), 0)
    circles = cv2.HoughCircles(
        blur, cv2.HOUGH_GRADIENT, dp=1.5, minDist=max(h, w),
        param1=60, param2=40,
        minRadius=int(min(h, w) * 0.10), maxRadius=int(min(h, w) * 0.48),
    )
    if circles is not None:
        x, y, r = np.round(circles[0][0]).astype(int)
        return int(x), int(y), int(r)

    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise BlastocystNotFound("no circle and no contour found")
    (x, y), r = cv2.minEnclosingCircle(max(contours, key=cv2.contourArea))
    if r < min(h, w) * 0.05:
        raise BlastocystNotFound(f"largest contour radius {r:.0f}px is implausibly small")
    return int(x), int(y), int(r)


def _disc(shape, cx, cy, radius) -> np.ndarray:
    mask = np.zeros(shape, dtype=np.uint8)
    cv2.circle(mask, (cx, cy), int(radius), 255, -1)
    return mask.astype(bool)


def segment_icm(grey: np.ndarray, inner: np.ndarray) -> tuple[np.ndarray, int]:
    """Watershed-segment the inner cell mass inside the trophectoderm disc.

    Returns the ICM mask and the watershed region count (WSN), which is itself
    a texture descriptor: a fragmented interior yields many basins.
    """
    from skimage.feature import peak_local_max
    from skimage.segmentation import watershed
    from scipy import ndimage

    values = grey[inner]
    if values.size == 0:
        return np.zeros_like(inner), 0

    # The ICM is denser and darker than surrounding trophectoderm.
    threshold = np.percentile(values, 30)
    dark = (grey <= threshold) & inner
    dark = ndimage.binary_opening(dark, np.ones((5, 5)))
    dark = ndimage.binary_closing(dark, np.ones((9, 9)))

    distance = ndimage.distance_transform_edt(dark)
    if distance.max() <= 0:
        return np.zeros_like(inner), 0

    coords = peak_local_max(distance, labels=dark, min_distance=15)
    markers = np.zeros_like(distance, dtype=int)
    for i, (r, c) in enumerate(coords, start=1):
        markers[r, c] = i
    labels = watershed(-distance, markers, mask=dark)
    n_regions = int(labels.max())
    if n_regions == 0:
        return np.zeros_like(inner), 0

    # The ICM is the largest coherent basin.
    sizes = ndimage.sum(np.ones_like(labels), labels, index=range(1, n_regions + 1))
    return labels == (int(np.argmax(sizes)) + 1), n_regions


def _masked_glcm(grey: np.ndarray, mask: np.ndarray, distance: int = GLCM_DISTANCE) -> dict:
    """GLCM texture using only pixel pairs where *both* ends lie in the mask.

    Cropping to a bounding box would drag in background and quietly change the
    texture of a ring-shaped region, which is exactly the shape used here.
    """
    if mask.sum() < 50:
        return {"contrast": 0.0, "correlation": 0.0, "energy": 0.0, "homogeneity": 0.0}

    q = (grey.astype(np.float64) / 256 * GLCM_LEVELS).astype(np.int32)
    q = np.clip(q, 0, GLCM_LEVELS - 1)

    matrix = np.zeros((GLCM_LEVELS, GLCM_LEVELS), dtype=np.float64)
    for dy, dx in ((0, distance), (distance, 0), (distance, distance), (-distance, distance)):
        a = q[max(0, -dy):q.shape[0] - max(0, dy), max(0, -dx):q.shape[1] - max(0, dx)]
        b = q[max(0, dy):q.shape[0] - max(0, -dy), max(0, dx):q.shape[1] - max(0, -dx)]
        ma = mask[max(0, -dy):mask.shape[0] - max(0, dy), max(0, -dx):mask.shape[1] - max(0, dx)]
        mb = mask[max(0, dy):mask.shape[0] - max(0, -dy), max(0, dx):mask.shape[1] - max(0, -dx)]
        both = ma & mb
        if both.any():
            np.add.at(matrix, (a[both], b[both]), 1)

    total = matrix.sum()
    if total == 0:
        return {"contrast": 0.0, "correlation": 0.0, "energy": 0.0, "homogeneity": 0.0}
    p = matrix / total

    i, j = np.meshgrid(np.arange(GLCM_LEVELS), np.arange(GLCM_LEVELS), indexing="ij")
    mu_i, mu_j = (p * i).sum(), (p * j).sum()
    sd_i = np.sqrt((p * (i - mu_i) ** 2).sum())
    sd_j = np.sqrt((p * (j - mu_j) ** 2).sum())
    correlation = (
        float((p * (i - mu_i) * (j - mu_j)).sum() / (sd_i * sd_j)) if sd_i > 0 and sd_j > 0 else 0.0
    )
    return {
        "contrast": float((p * (i - j) ** 2).sum()),
        "correlation": correlation,
        "energy": float((p ** 2).sum()),
        "homogeneity": float((p / (1.0 + (i - j) ** 2)).sum()),
    }


def _grey_stats(grey: np.ndarray, mask: np.ndarray) -> dict:
    """Distribution of intensity within a region.

    ``dark`` and ``bright`` are the fractions below/above one standard
    deviation from the region mean — a scale-free way to say how mottled the
    region is, which is what an embryologist reads as cellular detail.
    """
    values = grey[mask]
    if values.size == 0:
        return {k: 0.0 for k in ("deviation", "mean", "mode", "dark", "bright", "count")}
    mean, sd = float(values.mean()), float(values.std())
    counts = np.bincount(values, minlength=256)
    return {
        "deviation": sd,
        "mean": mean,
        "mode": float(int(np.argmax(counts))),
        "dark": float((values < mean - sd).mean()),
        "bright": float((values > mean + sd).mean()),
        "count": float(values.size),
    }


def _cluster_descriptors(grey: np.ndarray, inner: np.ndarray) -> dict:
    """Dark and light cluster counts and mean sizes at two thresholds.

    Stands in for the paper's DC/LC variables: connected dark and light blobs
    inside the embryo at a tight and a loose cut-off. Blob structure is how
    cellular granularity shows up numerically.
    """
    from scipy import ndimage

    out = {}
    values = grey[inner]
    if values.size == 0:
        return {k: 0.0 for k in ("DC1", "Mean DC1", "LC1", "Mean LC1", "DC2", "Mean DC2", "LC2", "Mean LC2")}
    mean, sd = values.mean(), values.std()

    for index, k in enumerate((1.0, 0.5), start=1):
        for label, region in (
            ("DC", (grey < mean - k * sd) & inner),
            ("LC", (grey > mean + k * sd) & inner),
        ):
            cleaned = ndimage.binary_opening(region, np.ones((3, 3)))
            labelled, n = ndimage.label(cleaned)
            sizes = ndimage.sum(np.ones_like(labelled), labelled, index=range(1, n + 1)) if n else []
            out[f"{label}{index}"] = float(n)
            out[f"Mean {label}{index}"] = float(np.mean(sizes)) if n else 0.0
    return out


def extract_features(image_path: str | Path) -> dict[str, float]:
    """Compute the morphometric feature vector for one blastocyst image file."""
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"could not read image: {image_path}")
    return extract_features_from_bytes(cv2.imencode(".png", image)[1].tobytes())


def extract_features_from_bytes(image_bytes: bytes) -> dict[str, float]:
    """Measure an image held in memory.

    Serving must land on exactly the pixels training saw. An earlier version of
    the endpoint measured the *sanitised* copy — re-encoded to JPEG q95 to strip
    EXIF — and that lossy round-trip moved features enough to flip the predicted
    grade on 3 of 39 images, with confidence shifting by up to 0.47. Sanitising
    is right for what gets stored; it must not sit between the camera and the
    measurement.
    """
    buffer = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise BlastocystNotFound("image bytes could not be decoded")
    grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if grey.shape[1] != WORKING_WIDTH:
        scale = WORKING_WIDTH / grey.shape[1]
        grey = cv2.resize(
            grey,
            (WORKING_WIDTH, max(1, int(round(grey.shape[0] * scale)))),
            interpolation=cv2.INTER_AREA,
        )

    cx, cy, radius = locate_blastocyst(grey)
    er = _disc(grey.shape, cx, cy, radius)
    inner = _disc(grey.shape, cx, cy, radius * RR_INNER_FRACTION)
    rr = er & ~inner                      # outer annulus
    icm, watershed_count = segment_icm(grey, inner)
    te = inner & ~icm                     # inner disc minus the mass

    features: dict[str, float] = {}

    features["Radius ER"] = float(radius)
    features["Sum ER"] = float(er.sum())
    features["Mean grey ER"] = float(grey[er].mean()) if er.any() else 0.0

    for region, mask, mode_key in (("RR", rr, "Mode value RR"), ("TE", te, "Mode grey TE")):
        glcm = _masked_glcm(grey, mask)
        features[f"Contrast {region}"] = glcm["contrast"]
        features[f"Correlation {region}"] = glcm["correlation"]
        features[f"Energy {region}"] = glcm["energy"]
        features[f"Homogeneity {region}"] = glcm["homogeneity"]
        stats = _grey_stats(grey, mask)
        features[f"Deviation {region}"] = stats["deviation"]
        features[f"Mean grey {region}"] = stats["mean"]
        features[mode_key] = stats["mode"]
        features[f"Dark {region}"] = stats["dark"]
        features[f"Bright {region}"] = stats["bright"]
        features[f"Mean Count {region}"] = stats["count"]

    area = float(icm.sum())
    features["Area ICM"] = area / float(er.sum()) if er.any() else 0.0
    features["Mean ICM"] = float(grey[icm].mean()) if icm.any() else 0.0
    if area > 0:
        contours, _ = cv2.findContours(
            icm.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        blob = max(contours, key=cv2.contourArea)
        hull_area = cv2.contourArea(cv2.convexHull(blob))
        features["Convex ICM"] = area / hull_area if hull_area > 0 else 0.0
        if len(blob) >= 5:
            (_, _), (major, minor), _ = cv2.fitEllipse(blob)
            major, minor = max(major, minor), min(major, minor)
            features["Eccen ICM"] = (
                float(np.sqrt(1 - (minor / major) ** 2)) if major > 0 else 0.0
            )
        else:
            features["Eccen ICM"] = 0.0
    else:
        features["Convex ICM"] = 0.0
        features["Eccen ICM"] = 0.0

    features.update(_cluster_descriptors(grey, inner))
    features["WSN"] = float(watershed_count)

    return {name: float(features.get(name, 0.0)) for name in FEATURE_NAMES}
