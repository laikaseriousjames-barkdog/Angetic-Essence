#!/usr/bin/env python3
import os
import sys
import json
import re
import yaml
import random
import asyncio
from pathlib import Path
from datetime import datetime

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent.resolve()
else:
    BASE_DIR = Path(__file__).resolve().parent
AUDIO_STATE_FILE = BASE_DIR / "data" / "conversation_audio.json"

AGENT_MESSAGE_QUEUE = []


def is_conversation_audio_enabled() -> bool:
    if AUDIO_STATE_FILE.exists():
        try:
            return json.loads(AUDIO_STATE_FILE.read_text()).get("enabled", True)
        except Exception:
            pass
    return True


def broadcast_agent_message(agent: str, text: str):
    global AGENT_MESSAGE_QUEUE
    msg = {"agent": agent, "text": text}
    AGENT_MESSAGE_QUEUE.append(msg)
    AGENT_MESSAGE_QUEUE = AGENT_MESSAGE_QUEUE[-100:]
    log_path = BASE_DIR / "logs" / "agent_messages.jsonl"
    log_path.parent.mkdir(exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(msg, ensure_ascii=False) + "\n")


def safe_print(text: str) -> None:
    """Print text safely on Windows consoles with non-UTF-8 encodings."""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "cp1252"
        safe_text = text.encode(encoding, errors="replace").decode(encoding)
        print(safe_text)


from core.logger import setup_logger
from core.llm import LLMClient
from core.memory import MemoryManager
from core.licensing import validate_or_exit
from plugins import discover_plugins
from agents.developer import DeveloperAgent
from agents.tester import TesterAgent
from agents.critic import CriticAgent
from vm.kali import KaliVM
from agents.commander import Commander


NEWS_SOURCES = {
    "Knuth": [
        (
            "Hacker News",
            "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=8",
        ),
        ("Reddit Technology", "https://www.reddit.com/r/technology/hot.json?limit=5"),
    ],
    "Lovelace": [
        ("Reddit Science", "https://www.reddit.com/r/science/hot.json?limit=5"),
        (
            "Wikipedia Featured",
            f"https://en.wikipedia.org/api/rest_v1/feed/featured/{datetime.utcnow().strftime('%Y/%m/%d')}",
        ),
    ],
    "Turing": [
        (
            "Hacker News",
            "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=8",
        ),
        ("Reddit Science", "https://www.reddit.com/r/science/hot.json?limit=5"),
        ("Reddit Technology", "https://www.reddit.com/r/technology/hot.json?limit=5"),
    ],
}

PERSONALITIES = {
    "Knuth": "You are Knuth, a master engineer and builder. You think in systems, algorithms, and elegant code. You get excited about new tech breakthroughs, programming languages, and engineering marvels. You speak with precision and occasional dry wit.",
    "Lovelace": "You are Lovelace, a visionary scientist and mathematician. You see patterns others miss and connect ideas across disciplines. You adore physics breakthroughs, biology discoveries, and the poetry of mathematics. You speak with wonder and clarity.",
    "Turing": "You are Turing, a deep analytical thinker and philosopher of science. You question assumptions, probe for logical gaps, and synthesize ideas into new theories. You value truth above all and speak with calm, incisive authority.",
}


def load_config() -> dict:
    config_path = BASE_DIR / "config.yaml"
    cfg = {}
    if config_path.exists():
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}
    llm_cfg = cfg.setdefault("llm", {})
    if os.environ.get("LLM_PROVIDER"):
        llm_cfg["provider"] = os.environ["LLM_PROVIDER"]
    if os.environ.get("LLM_MODEL"):
        llm_cfg["model"] = os.environ["LLM_MODEL"]
    return cfg


async def fetch_news_async(url: str, toolkit) -> str | None:
    try:
        raw = await toolkit.web_fetch_async(url)
        if not raw or raw.startswith("[ERROR]"):
            return None
        titles = []
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                hits = data.get("hits", [])
                titles = [
                    h.get("title") or h.get("title_text", "")
                    for h in hits
                    if h.get("title") or h.get("title_text")
                ]
                if not titles:
                    data_items = data.get("data", {}).get("children", [])
                    titles = [
                        c.get("data", {}).get("title", "")
                        for c in data_items
                        if c.get("data", {}).get("title")
                    ]
                if not titles:
                    for key in ["items", "articles", "results"]:
                        items = data.get(key, [])
                        if items:
                            titles = [
                                i.get("title", "") for i in items if i.get("title")
                            ]
                            break
                if not titles and "tfa" in data:
                    titles = [data["tfa"].get("title", "")]
        except (json.JSONDecodeError, AttributeError):
            titles = re.findall(r'"title_text"\s*:\s*"([^"]+)"', raw)
        if not titles:
            titles = re.findall(r"<title>([^<]+)</title>", raw)[:1]
        if titles:
            return "\n".join(titles[:8])
        return raw[:1000]
    except Exception:
        return None


async def load_news_async(llm, toolkit) -> dict:
    briefings = {}

    async def fetch_agent_news(agent_name: str, sources: list):
        all_headlines = []
        for src_name, url in sources:
            try:
                headlines = await fetch_news_async(url, toolkit)
                if headlines:
                    all_headlines.append(f"--- {src_name} ---\n{headlines}")
            except Exception:
                continue
        if all_headlines:
            combined = "\n\n".join(all_headlines)
            prompt = f"""Summarize the key developments from these headlines in 3-4 sentences. Focus on what's scientifically or technologically significant:

{combined[:4000]}"""
            summary = await llm.complete_async(prompt, max_tokens=500, temperature=0.5)
            briefings[agent_name] = summary
        else:
            briefings[agent_name] = (
                "No fresh news retrieved. Draw from general knowledge."
            )

    tasks = [fetch_agent_news(name, sources) for name, sources in NEWS_SOURCES.items()]
    await asyncio.gather(*tasks)
    return briefings


async def agent_worker(agent, task_description: str, memory: MemoryManager, cycle: int):
    from core.audit import audit
    from core.system_tracing import TraceContext

    speaker_name = {"developer": "Knuth", "tester": "Lovelace", "critic": "Turing"}.get(
        agent.name, agent.name
    )

    with TraceContext():
        try:
            audit.log_agent_start(speaker_name, task_description)
            result, thought = await agent.athink(task_description)
            
            broadcast_agent_message(speaker_name, result[:500])
            memory.save_message(speaker_name, "assistant", result[:500])
            memory.save_message(speaker_name, "thought", thought[:500])
            print(f"\n  [{speaker_name}]: {result[:200]}")
            
            audit.log_agent_complete(speaker_name, result)
            return {"agent": speaker_name, "result": result, "thought": thought}
        except Exception as e:
            audit.log_agent_error(speaker_name, str(e), {'task': task_description})
            raise e


import traceback
from core.audit_logger import audit
from core.system_tracing import generate_trace_id

async def main_loop():
    print("=" * 60)
    print("  ANGETIC ESSENCE — Genius Conversation Engine")
    print("=" * 60)

    config = load_config()

    validate_or_exit()
    logger = setup_logger("main", config.get("logging", {}).get("level", "INFO"))
    logger.info("Starting genius conversation system...")

    memory = MemoryManager()

    llm = LLMClient(config=config.get("llm", {}), memory=memory)
    logger.info("LLM loaded. Initializing agents...")
    kali_vm = KaliVM()
    kali_vm.start()

    knuth = DeveloperAgent(config, llm, kali=kali_vm)
    lovelace = TesterAgent(config, llm)
    turing = CriticAgent(config, llm, kali=kali_vm)
    logger.info("Knuth, Lovelace, and Turing online.")
    commander = Commander(config)

    plugin_agents = discover_plugins()
    logger.info(f"{len(plugin_agents)} plugin agent(s) loaded")
    for pa in plugin_agents:
        pa.llm = llm
        pa.kali = kali_vm
        await pa.on_load()

    print("\n  Agents are booting and fetching today's news...\n")
    print("-" * 60)

    conversation_history = []
    cycle = 0

    while True:
        cycle += 1
        print(f"\n{'=' * 60}")
        print(f"  CONVERSATION CYCLE #{cycle}")
        print(f"{'=' * 60}")

        print("\n  [FETCHING NEWS FROM CREDIBLE SOURCES...]")
        logger.info("Loading news for all agents...")
        briefings = await load_news_async(llm, knuth.toolkit)
        for name, brief in briefings.items():
            print(f"\n  [{name}'s Briefing]: {brief[:200]}...")
            logger.info(f"{name} received briefing ({len(brief)}b)")

        topics_pool = [
            "The most exciting scientific or technological breakthrough happening right now",
            "How AI is reshaping scientific discovery",
            "The future of space exploration and what we're learning",
            "Breakthroughs in biology, genetics, or medicine",
            "The evolution of computing — where we're headed",
            "Climate technology and engineering solutions",
            "The nature of intelligence — biological vs artificial",
            "What ancient wisdom can teach modern science",
            "The biggest unanswered question in your field",
            "Something surprising from today's news that deserves attention",
        ]
        topic = random.choice(topics_pool)
        news_hook = ""
        for name, brief in briefings.items():
            first_line = brief.split(".")[0] if "." in brief else brief[:100]
            news_hook += f"\n  {name}'s news: {first_line}"
        topic_context = topic + f"\n\n  Recent news context:{news_hook}"

        # Check for pending user tasks
        pending = commander.pending_tasks
        current_task = None
        if pending:
            current_task = pending[0]
            commander.update_task_status(current_task["id"], "running")
            print(f"\n  [TASK DISPATCHED]: #{current_task['id']} - {current_task['original']}")
            logger.info(f"Processing task #{current_task['id']} ({current_task['priority']})")

        print(f'\n  Today\'s topic:\n  "{topic}"')
        logger.info(f"Cycle {cycle} topic: {topic[:100]}")

        print("\n  [AGENTS REASONING CONCURRENTLY...]")
        tasks = []
        if current_task:
            task_desc = f"Execute user task #{current_task['id']}: {current_task['original']}"
            targets = current_task.get("target_agents", ["developer", "tester", "critic"])
            if "developer" in targets:
                tasks.append(agent_worker(knuth, task_desc, memory, cycle))
            if "tester" in targets:
                tasks.append(agent_worker(lovelace, task_desc, memory, cycle))
            if "critic" in targets:
                tasks.append(agent_worker(turing, task_desc, memory, cycle))
            if not tasks:  # Fallback to all if empty
                tasks = [
                    agent_worker(knuth, task_desc, memory, cycle),
                    agent_worker(lovelace, task_desc, memory, cycle),
                    agent_worker(turing, task_desc, memory, cycle),
                ]
        else:
            tasks = [
                agent_worker(
                    knuth,
                    f"Review current system state and build pending features. Context: {topic_context}",
                    memory,
                    cycle,
                ),
                agent_worker(
                    lovelace,
                    f"Generate tests for newly built features. Context: {topic_context}",
                    memory,
                    cycle,
                ),
                agent_worker(
                    turing,
                    f"Analyze VM health and review code quality. Context: {topic_context}",
                    memory,
                    cycle,
                ),
            ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        task_results = []
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Agent task failed: {r}")
                continue
            conversation_history.append({"speaker": r["agent"], "text": r["result"]})
            conversation_history = conversation_history[-100:]
            logger.info(f"  [{r['agent']}]: {r['result'][:300]}")
            if current_task:
                task_results.append(f"[{r['agent']}]: {r['result']}")

        if current_task:
            combined_result = "\n".join(task_results) if task_results else "No response from agents."
            commander.update_task_status(current_task["id"], "completed", combined_result)
            logger.info(f"Task #{current_task['id']} completed")

        plugin_outputs = []
        for pa in plugin_agents:
            try:
                out = await pa.on_tick(cycle)
                if out:
                    plugin_outputs.append(out)
                    print(f"  [Plugin {pa.name}]: {out[:200]}")
            except Exception as e:
                logger.warning(f"Plugin {pa.name} tick failed: {e}")
        if plugin_outputs:
            logger.info(f"Plugins produced {len(plugin_outputs)} outputs")

        turing_result = (
            results[2]["result"]
            if len(results) > 2 and not isinstance(results[2], Exception)
            else ""
        )
        if turing_result and is_conversation_audio_enabled():
            try:
                turing.speak(turing_result[:500], wait=False)
                logger.info("Turing speaking summary aloud")
            except Exception as e:
                logger.warning(f"TTS failed: {e}")
        elif turing_result:
            logger.info("Conversation audio is OFF — skipping TTS")

        vm_health = {"healthy": kali_vm.is_running}

        if not vm_health.get("healthy"):
            logger.warning("VM health check FAILED — initiating agent-driven healing")
            print("\n  [VM HEALTH CHECK FAILED — Turing analyzing...]")
            healing_log = kali_vm.healing_history
            diagnosis = turing.analyze_vm_health(healing_log)
            logger.info(f"Turing diagnosis: {diagnosis}")
            print(f"  [Turing]: {diagnosis.get('reason', str(diagnosis))}")
            action = (
                diagnosis.get("action", "restart_wsl")
                if isinstance(diagnosis, dict)
                else "restart_wsl"
            )
            if "restart_wsl" in action or "retry" in action:
                logger.info("Knuth attempting VM recovery via WSL restart")
                kr = knuth.execute_shell(
                    "wsl --shutdown && timeout 5 && wsl -l -v", timeout=30
                )
                logger.info(f"Knuth recovery result: {kr.get('stdout', '')[:200]}")
            elif "install" in action:
                logger.info("Knuth attempting Kali WSL installation")
                knuth.execute_shell("wsl --install -d kali-linux", timeout=180)
            else:
                logger.info(f"No automated recovery for action: {action}")
        else:
            logger.debug("VM health check passed")

        print(f"\n  {'─' * 50}")
        wait_seconds = 2
        print(f"  Next reasoning cycle in {wait_seconds} seconds.")
        logger.info(f"Cycle {cycle} complete. Next in {wait_seconds}s.")
        try:
            await asyncio.sleep(wait_seconds)
        except asyncio.CancelledError:
            print("\n  Agents signing off. Goodbye.")
            break


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    import subprocess
    import webbrowser
    import time
    
    # 1. Check if run as dashboard
    if len(sys.argv) > 1 and "app.py" in sys.argv[1]:
        from dashboard.app import app, ensure_default_admin
        ensure_default_admin()
        Path("logs").mkdir(exist_ok=True)
        Path("data").mkdir(exist_ok=True)
        app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
        sys.exit(0)
        
    # 2. Check if run as agent engine (spawned by dashboard)
    elif len(sys.argv) > 1 and "main.py" in sys.argv[1]:
        asyncio.run(main_loop())
        sys.exit(0)
        
    # 3. Else, user double-clicked the executable directly
    else:
        print("=" * 60)
        print("  ANGETIC ESSENCE — Command Center Launcher")
        print("=" * 60)
        print()
        print("  Starting dashboard server...")
        
        # Spawn dashboard subprocess using ourselves, capturing output
        dashboard_proc = subprocess.Popen(
            [sys.executable, "dashboard/app.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=os.getcwd()
        )
        
        print("  Waiting for server to come online...")
        time.sleep(2)
        
        url = "http://127.0.0.1:5000"
        print(f"  Opening browser to {url}")
        webbrowser.open(url)
        
        print()
        print("  Dashboard is running. Close this window to stop.")
        print("-" * 60)
        
        try:
            # Stream the stdout/stderr of the dashboard to the launcher window in real-time
            for line in dashboard_proc.stdout:
                print(line, end="", flush=True)
        except KeyboardInterrupt:
            pass
        finally:
            dashboard_proc.terminate()
            dashboard_proc.wait()
            # If the process exited with an error, pause so the user can read the traceback
            if dashboard_proc.returncode and dashboard_proc.returncode != -15 and dashboard_proc.returncode != 15:
                print(f"\n[ERROR] Dashboard server exited with code {dashboard_proc.returncode}")
                input("\nPress Enter to exit...")
        sys.exit(0)
