"""
MAMS - Matrix Agentic Money System
Startup Script
"""

import os
import sys
import argparse
import subprocess
import threading
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def run_system(mode="autonomous", port=None):
    """Run the main system"""
    if port is None:
        import os
        port = int(os.getenv("PORT", 8050))
    print("=" * 60)
    print("🚀 MAMS - Matrix Agentic Money System")
    print("=" * 60)
    print(f"Mode: {mode}")
    print()
    
    # Check for config file
    config_path = Path("config.yaml")
    if not config_path.exists():
        print("⚠️  config.yaml not found, copying from example...")
        example = Path(".env.example")
        if example.exists():
            import shutil
            shutil.copy(".env.example", ".env")
            print("✅ Created .env file - please add your API keys!")
    
    # Run dashboard in background
    print("📊 Starting Dashboard Server...")
    dashboard_thread = threading.Thread(
        target=run_dashboard,
        args=(port,),
        daemon=True
    )
    dashboard_thread.start()
    
    print(f"✅ Dashboard available at: http://localhost:{port}")
    print()
    
    # Import and run main system
    print("🔄 Starting Agent System...")
    try:
        from main import SystemOrchestrator
        
        orchestrator = SystemOrchestrator()
        orchestrator.on_alert = lambda msg: print(f"⚠️  ALERT: {msg}")
        orchestrator.initialize()
        orchestrator.start()
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested...")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


def run_dashboard(port=8050):
    """Run the dashboard only"""
    from dashboard import app
    app.run(debug=False, port=port, host='0.0.0.0')


def run_agent(agent_id):
    """Run a single agent"""
    print(f"Starting single agent: {agent_id}")
    from agents import (
        ResearcherAgent, CreatorAgent, MarketerAgent, 
        SalesAgent, AnalystAgent, QualityAgent, 
        ComplianceAgent, FinanceAgent
    )
    
    agents = {
        "researcher": ResearcherAgent,
        "creator": CreatorAgent,
        "marketer": MarketerAgent,
        "sales": SalesAgent,
        "analyst": AnalystAgent,
        "quality": QualityAgent,
        "compliance": ComplianceAgent,
        "finance": FinanceAgent,
    }
    
    agent_class = agents.get(agent_id)
    if not agent_class:
        print(f"Unknown agent: {agent_id}")
        return
    
    agent = agent_class()
    agent.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()


def test_system():
    """Run system tests"""
    print("🧪 Running System Tests...")
    print()
    
    # Test imports
    print("1. Testing imports...")
    try:
        from config import get_config
        from memory import get_memory
        from message_bus import get_message_bus
        from base_agent import BaseAgent
        from agents import ResearcherAgent, CreatorAgent, MarketerAgent
        from director import DirectorAgent
        from main import SystemOrchestrator
        print("   ✅ All imports successful")
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return
    
    # Test config
    print("2. Testing configuration...")
    try:
        config = get_config()
        print(f"   ✅ Config loaded: {config.system.name}")
    except Exception as e:
        print(f"   ⚠️  Config warning: {e}")
    
    # Test memory
    print("3. Testing memory system...")
    try:
        memory = get_memory()
        memory.store_shared("test", "hello")
        result = memory.retrieve("test")
        print(f"   ✅ Memory working: {result}")
    except Exception as e:
        print(f"   ❌ Memory failed: {e}")
    
    # Test message bus
    print("4. Testing message bus...")
    try:
        bus = get_message_bus()
        bus.register_agent("test_agent", "test")
        print("   ✅ Message bus working")
    except Exception as e:
        print(f"   ❌ Message bus failed: {e}")
    
    # Test agents
    print("5. Testing agents...")
    try:
        researcher = ResearcherAgent()
        result = researcher.execute_task("scan_trends", "Test scan", {"keywords": ["AI"]})
        print(f"   ✅ Researcher working: {result.get('trends_found', 0)} trends")
        
        creator = CreatorAgent()
        result = creator.execute_task("create_blog_post", "Test post", {"topic": "AI"})
        print(f"   ✅ Creator working: {result.get('content_id', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Agent test failed: {e}")
    
    # Test revenue engine
    print("6. Testing revenue engine...")
    try:
        from revenue import get_revenue_engine
        engine = get_revenue_engine()
        result = engine.generate_affiliate_revenue(1000, 20)
        print(f"   ✅ Revenue engine working: ${result.amount:.2f}")
    except Exception as e:
        print(f"   ❌ Revenue test failed: {e}")
    
    print()
    print("=" * 60)
    print("✅ System tests completed!")
    print("=" * 60)


def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    
    requirements = [
        "openai>=1.0.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
        "pandas>=2.0.0",
        "loguru>=0.7.0",
        "rich>=13.0.0",
        "dash>=2.14.0",
        "plotly>=5.18.0",
        "schedule>=1.2.0",
        "tenacity>=8.2.0",
        "httpx>=0.25.0",
        "Pillow>=10.0.0",
    ]
    
    for req in requirements:
        print(f"   Installing {req}...")
        subprocess.run([sys.executable, "-m", "pip", "install", req], check=False)
    
    print("✅ Dependencies installed!")


def main():
    parser = argparse.ArgumentParser(description="MAMS - Matrix Agentic Money System")
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "dashboard", "agent", "test", "install"],
        help="Command to run"
    )
    parser.add_argument("--agent", type=str, help="Agent ID to run")
    parser.add_argument("--port", type=int, default=8050, help="Dashboard port")
    parser.add_argument("--mode", type=str, default="autonomous", help="System mode")
    
    args = parser.parse_args()
    
    if args.command == "run":
        run_system(mode=args.mode, port=args.port)
    elif args.command == "dashboard":
        run_dashboard(port=args.port)
    elif args.command == "agent":
        if not args.agent:
            print("Error: --agent required for 'agent' command")
            return
        run_agent(args.agent)
    elif args.command == "test":
        test_system()
    elif args.command == "install":
        install_dependencies()


if __name__ == "__main__":
    main()
