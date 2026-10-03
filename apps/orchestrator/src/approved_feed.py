from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / 'apps' / 'orchestrator' / 'src'
sys.path.insert(0, str(SRC_DIR))

from main import ingest_approved_sources_from_directory


def main() -> None:
    feed_dir = PROJECT_ROOT / 'data' / 'approved_sources'
    reviews = ingest_approved_sources_from_directory(
        feed_dir,
        source_name='Approved Resource Feed',
        category='general',
        source_url_prefix='https://approved.example.org/resources',
        tags='approved-source, rights, wellbeing, support',
    )

    print(f'Created {len(reviews)} review entries from approved feed.')
    for review in reviews:
        print(f"- {review['title']} | status={review['status']} | source={review['source']}")


if __name__ == '__main__':
    main()
