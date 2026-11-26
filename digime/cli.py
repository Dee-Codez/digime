import argparse
import os
import re
from pathlib import Path

import yaml

from digime.ingest.takeout import ingest_takeout
from digime.ingest.browser_history import load_chrome_history
from digime.query.chat import answer
from digime.graph.graph import Graph
from digime.graph.schema import create_schema
from digime.graph.builder import build_statements
from digime.graph.query import run_named, run_raw, NAMED_QUERIES
from digime.store.embed import Embedder


_ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _expand_env(value):
    """Recursively replace ${VAR} references with values from the environment.

    Keeps credentials out of tracked files: config.yaml can say
    ``password: ${NEO4J_PASSWORD}`` and the real value comes from the env.
    """
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    if isinstance(value, str):
        return _ENV_REF.sub(lambda m: os.environ.get(m.group(1), ""), value)
    return value


def _load_config(config_path: str) -> dict:
    with open(config_path) as f:
        return _expand_env(yaml.safe_load(f))


def _collect_memories(cfg) -> list:
    memories = []

    takeout_cfg = cfg["sources"]["takeout"]
    if takeout_cfg.get("enabled") and takeout_cfg.get("path"):
        td = Path(takeout_cfg["path"]).expanduser()
        if td.exists():
            mems = ingest_takeout(td)
            memories.extend(mems)
            print(f"[takeout] collected {len(mems)} memories from {td}")
        else:
            print(f"[takeout] path not found: {td}")

    browser_cfg = cfg["sources"]["browser_history"]
    if browser_cfg.get("enabled") and browser_cfg.get("chrome_profile"):
        cp = Path(browser_cfg["chrome_profile"]).expanduser()
        try:
            mems = list(
                load_chrome_history(
                    cp,
                    youtube_only=browser_cfg.get("youtube_only", False),
                    limit=browser_cfg.get("limit_per_run", 10000),
                )
            )
            memories.extend(mems)
            print(f"[browser] collected {len(mems)} memories from {cp}")
        except FileNotFoundError as e:
            print(f"[browser] {e}")

    return memories


def _get_graph(cfg) -> Graph:
    ncfg = cfg["neo4j"]
    password = ncfg.get("password") or os.environ.get("NEO4J_PASSWORD", "")
    if not password:
        raise SystemExit(
            "Neo4j password not set. Export NEO4J_PASSWORD or set "
            "neo4j.password in config.yaml (see config.example.yaml)."
        )
    return Graph(
        ncfg.get("uri", "bolt://localhost:7687"),
        ncfg.get("user", "neo4j"),
        password,
        ncfg.get("database", "neo4j"),
    )


def cmd_ingest(args):
    cfg = _load_config(args.config)
    memories = _collect_memories(cfg)
    if not memories:
        print("No memories collected. Check config.yaml source paths.")
        return

    embedder = Embedder()
    graph = _get_graph(cfg)
    try:
        create_schema(graph, embed_dim=embedder.dim)
        statements = build_statements(memories, embedder, cfg["neo4j"].get("me_email", ""))
        graph.exec_many(statements)
        print(f"[neo4j] wrote {len(statements)} statements (graph + embeddings)")
    finally:
        graph.close()


def cmd_ask(args):
    cfg = _load_config(args.config)
    embedder = Embedder()
    graph = _get_graph(cfg)
    try:
        vec = embedder.embed_one(args.question)
        results = graph.vector_search("memory_embeddings", vec, cfg["retrieval"]["top_k"])
    finally:
        graph.close()

    llm = cfg["llm"]
    print(
        answer(
            args.question,
            results,
            ollama_model=llm.get("ollama_model", ""),
            ollama_base_url=llm.get("ollama_base_url", "http://localhost:11434"),
        )
    )


def cmd_graph(args):
    cfg = _load_config(args.config)
    graph = _get_graph(cfg)
    try:
        if args.query:
            for row in run_named(args.query, args.params or {}, graph):
                print(row)
        elif args.cypher:
            for row in run_raw(args.cypher, graph):
                print(row)
        else:
            print("Available named queries:", ", ".join(NAMED_QUERIES))
    finally:
        graph.close()


def main():
    parser = argparse.ArgumentParser(prog="digime")
    parser.add_argument("--config", default="config.yaml")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Ingest Takeout + browser history into Neo4j")
    p_ingest.set_defaults(func=cmd_ingest)

    p_ask = sub.add_parser("ask", help="Ask your persona memory (vector search in Neo4j)")
    p_ask.add_argument("question", nargs="+")
    p_ask.set_defaults(func=cmd_ask)

    p_graph = sub.add_parser("graph", help="Query the Neo4j knowledge graph")
    p_graph.add_argument("--query", choices=sorted(NAMED_QUERIES), help="Named query")
    p_graph.add_argument("--param", action="append", nargs=2, metavar=("KEY", "VALUE"), dest="params_list")
    p_graph.add_argument("--cypher", help="Raw Cypher query")
    p_graph.set_defaults(func=cmd_graph)

    args = parser.parse_args()
    if args.command == "ask":
        args.question = " ".join(args.question)
    if args.command == "graph":
        args.params = dict(args.params_list) if getattr(args, "params_list", None) else None
    args.func(args)


if __name__ == "__main__":
    main()
