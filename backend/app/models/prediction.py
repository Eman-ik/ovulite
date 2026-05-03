from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.et_transfer import ETTransfer


class Prediction(Base):
    __tablename__ = "predictions"

    prediction_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transfer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("et_transfers.transfer_id")
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[Optional[str]] = mapped_column(String(50))
    probability: Mapped[Decimal] = mapped_column(nullable=False)
    confidence_lower: Mapped[Optional[Decimal]] = mapped_column()
    confidence_upper: Mapped[Optional[Decimal]] = mapped_column()
    risk_band: Mapped[Optional[str]] = mapped_column(String(20))
    shap_json: Mapped[Optional[Any]] = mapped_column(JSON)
    predicted_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    transfer: Mapped[Optional["ETTransfer"]] = relationship(
        back_populates="predictions"
    )
