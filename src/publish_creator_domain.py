from __future__ import annotations

import argparse

from sending_records import CreatorDelivery, client_from_environment, publish_domain, records_for


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish a creator delivery domain")
    parser.add_argument("domain")
    args = parser.parse_args()
    delivery = CreatorDelivery(creator_id="cli", domain=args.domain, job_id="manual")
    result = publish_domain(client_from_environment(), records_for(delivery.domain))
    print(f"zone_id={result.zone_id} verification={result.verification_status}")


if __name__ == "__main__":
    main()
