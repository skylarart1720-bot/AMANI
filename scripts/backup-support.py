"""Local wrapper for the same backup command shipped in the orchestrator image."""
import sys
from pathlib import Path
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env')
sys.path.insert(0,str(ROOT/'apps/orchestrator/src'))
from backup import main
if __name__=='__main__':
    main()
