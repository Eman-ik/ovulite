"""Create an organization and its first administrator. Run by the platform operator.

Organizations are no longer created over the API: a public endpoint could mint an
admin for anyone who asked. Run this from backend/ against the target database
(DATABASE_URL). The admin password is read from ADMIN_PASSWORD, is never printed,
and the admin is asked to change it at first login.

  ADMIN_PASSWORD='...' python scripts/create_organization.py \
      --name "Example Lab" --slug example-lab \
      --admin-username example_admin --admin-email admin@example.org
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth.password_policy import validate_password_strength  # noqa: E402
from app.auth.security import hash_password  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.organization import Organization, OrganizationMembership  # noqa: E402
from app.models.user import User  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--organization-type", default="lab")
    parser.add_argument("--country", default=None)
    parser.add_argument("--time-zone", default=None)
    parser.add_argument("--admin-username", required=True)
    parser.add_argument("--admin-full-name", default=None)
    parser.add_argument("--admin-email", default=None)
    args = parser.parse_args()

    password = os.environ.get("ADMIN_PASSWORD")
    if not password:
        print("Set ADMIN_PASSWORD to the first administrator's password.", file=sys.stderr)
        return 2
    validate_password_strength(password)

    db = SessionLocal()
    try:
        if db.query(Organization).filter(
            (Organization.name == args.name) | (Organization.slug == args.slug)
        ).first():
            print("An organization with that name or slug already exists.", file=sys.stderr)
            return 1
        if db.query(User).filter(User.username == args.admin_username).first() or (
            args.admin_email and db.query(User).filter(User.email == args.admin_email).first()
        ):
            print("That admin username or email is already in use.", file=sys.stderr)
            return 1

        organization = Organization(
            name=args.name,
            slug=args.slug,
            organization_type=args.organization_type,
            country=args.country,
            time_zone=args.time_zone,
        )
        db.add(organization)
        db.flush()

        admin = User(
            organization_id=organization.organization_id,
            username=args.admin_username,
            password_hash=hash_password(password),
            role="admin",
            full_name=args.admin_full_name,
            email=args.admin_email,
            must_change_password=True,
        )
        db.add(admin)
        db.flush()

        db.add(OrganizationMembership(
            organization_id=organization.organization_id,
            user_id=admin.user_id,
            role="admin",
            status="active",
            is_primary=True,
        ))
        db.commit()
        print(f"Created organization '{args.name}' (id {organization.organization_id}) "
              f"with administrator '{args.admin_username}'.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
