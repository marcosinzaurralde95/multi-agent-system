"""
MAMS - Matrix Agentic Money System
Director Agent (CEO)
"""

import hashlib
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import loguru

from base_agent import AgentCapability, BaseAgent, MessagePriority
from config import get_config
from memory import get_memory
from message_bus import get_message_bus

logger = loguru.logger


def _stable_score(seed: str, low: int = 1, high: int = 10) -> int:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    value = int(digest[:8], 16)
    return low + (value % (high - low + 1))


@dataclass
class RevenueGoal:
    target: float
    current: float
    period: str
    progress: float = 0
    on_track: bool = False

    def update(self, current: float):
        self.current = max(0.0, current)
        self.progress = (self.current / self.target * 100) if self.target > 0 else 0
        self.on_track = self.progress >= 50


@dataclass
class Decision:
    id: str
    decision_type: str
    description: str
    agents_involved: List[str]
    estimated_impact: float
    estimated_cost: float = 0.0  # Costo estimado de la decisión
    status: str
    created_at: datetime
    decided_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None


class DirectorAgent(BaseAgent):
    """Coordinates specialized agents and tracks strategy + revenue goals."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            agent_id="director",
            agent_type="director",
            name="Director Agent (CEO)",
            description="Chief Executive Orchestrator",
            capabilities=[AgentCapability.ANALYZE_DATA, AgentCapability.COMMUNICATION],
            config=config or {},
        )
        cfg = get_config()
        self.memory = get_memory()
        self.message_bus = get_message_bus()

        self.current_strategy: Dict[str, Any] = {}
        self.active_campaigns: List[str] = []
        self.pending_decisions: List[Decision] = []
        self.completed_decisions: List[Decision] = []

        self.revenue_goals: Dict[str, RevenueGoal] = {
            "daily": RevenueGoal(target=cfg.revenue_targets.daily, current=0, period="daily"),
            "weekly": RevenueGoal(target=cfg.revenue_targets.weekly, current=0, period="weekly"),
            "monthly": RevenueGoal(target=cfg.revenue_targets.monthly, current=0, period="monthly"),
        }

        # --- Guardrails & Budgeting ---
        self.daily_spend = 0.0
        self.last_budget_reset = datetime.now().date()
        self.max_daily_budget = cfg.system.max_daily_budget
        self.kill_switch = cfg.system.emergency_kill_switch
        # -----------------------------

        self.auto_approval_limit = float((config or {}).get("auto_approval_limit", 100))
        self.human_approval_limit = float((config or {}).get("human_approval_limit", 1000))

        self.on_approval_required: Optional[Callable] = None
        self.on_alert: Optional[Callable] = None

    def execute_task(self, task_type: str, description: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        handlers = {
            "strategic_planning": self._strategic_planning,
            "resource_allocation": self._resource_allocation,
            "opportunity_evaluation": self._evaluate_opportunity,
            "campaign_orchestration": self._orchestrate_campaign,
            "performance_review": self._performance_review,
            "risk_assessment": self._risk_assessment,
            "agent_coordination": self._coordinate_agents,
            "revenue_optimization": self._optimize_revenue,
        }
        handler = handlers.get(task_type, self._default_director)
        rule_result = handler(input_data)
        return self.enrich_with_llm(task_type, description, input_data, rule_result)

    def _strategic_planning(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        horizon = input_data.get("horizon", "90_days")
        focus_areas = [
            {
                "area": "content_scale",
                "action": "Increase content production and distribution cadence",
                "agent": "creator",
                "kpi": "articles_per_week",
                "target": 14,
            },
            {
                "area": "funnel_conversion",
                "action": "Optimize lead funnel and checkout flow",
                "agent": "sales",
                "kpi": "conversion_rate",
                "target": 3.0,
            },
            {
                "area": "channel_efficiency",
                "action": "Prioritize channels with highest ROI",
                "agent": "marketer",
                "kpi": "roas",
                "target": 2.5,
            },
        ]

        strategy = {
            "id": f"strategy_{int(time.time())}",
            "horizon": horizon,
            "focus_areas": focus_areas,
            "created_at": datetime.now().isoformat(),
        }
        self.current_strategy = strategy
        self.memory.store_shared("current_strategy", strategy, importance=0.9)
        self._assign_strategy_tasks(strategy)
        return {
            "strategy_id": strategy["id"],
            "focus_areas": focus_areas,
            "tasks_created": len(focus_areas),
        }

    def _resource_allocation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        total_budget = float(input_data.get("budget", 500))
        priorities = input_data.get("priorities", [])
        if not priorities:
            priorities = [{"agent": "marketer"}, {"agent": "creator"}, {"agent": "sales"}]

        weighted = []
        remaining = total_budget
        for index, priority in enumerate(priorities):
            weight = 0.45 if index == 0 else 0.275
            amount = round(total_budget * weight, 2)
            remaining -= amount
            weighted.append(
                {
                    "agent": priority.get("agent", "unknown"),
                    "amount": amount,
                    "tasks": priority.get("tasks", []),
                }
            )

        allocation = {"distribution": weighted, "reserve": round(max(remaining, 0), 2)}
        return {"allocation": allocation, "total_budget": total_budget}

    def _evaluate_opportunity(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        opportunity = input_data.get("opportunity", {})
        seed = str(opportunity)
        scores = {
            "market_size": _stable_score(seed + "market"),
            "competition": _stable_score(seed + "competition"),
            "timing": _stable_score(seed + "timing"),
            "resources_available": _stable_score(seed + "resources"),
            "monetization_potential": _stable_score(seed + "monetization"),
        }
        overall_score = round(sum(scores.values()) / len(scores), 2)
        decision_status = "pursue" if overall_score >= 6.5 else "defer"

        decision = Decision(
            id=f"opp_{int(time.time())}",
            decision_type="opportunity",
            description=str(opportunity),
            agents_involved=["researcher", "creator"],
            estimated_impact=float(overall_score * 500),
            status="pending",
            created_at=datetime.now(),
        )
        self.pending_decisions.append(decision)

        if decision.estimated_impact <= self.auto_approval_limit:
            self._auto_approve(decision)

        return {
            "decision_id": decision.id,
            "scores": scores,
            "overall_score": overall_score,
            "decision": decision_status,
        }

    def _orchestrate_campaign(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        campaign_name = input_data.get("name", "Campaign")
        campaign_id = f"campaign_{int(time.time())}"

        plan = [
            ("researcher", "scan_trends"),
            ("creator", "create_blog_post"),
            ("marketer", "social_distribution"),
            ("sales", "optimize_conversion"),
            ("analyst", "performance_report"),
        ]

        for agent_id, task_type in plan:
            self.message_bus.create_task(
                task_type=task_type,
                description=f"{campaign_name}: {task_type}",
                assigned_to=agent_id,
                priority=MessagePriority.HIGH,
                input_data={"campaign_id": campaign_id, "campaign_name": campaign_name},
                metadata={"campaign_id": campaign_id},
            )

        self.active_campaigns.append(campaign_id)
        return {
            "campaign_id": campaign_id,
            "name": campaign_name,
            "tasks_dispatched": len(plan),
        }

    def _performance_review(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        period = input_data.get("period", "weekly")
        agents_status = self.message_bus.get_agent_status()
        return {
            "period": period,
            "generated_at": datetime.now().isoformat(),
            "agents_online": len([a for a in agents_status.values() if a.get("status") == "online"]),
            "active_campaigns": len(self.active_campaigns),
            "revenue": {
                "daily": self.revenue_goals["daily"].current,
                "weekly": self.revenue_goals["weekly"].current,
                "monthly": self.revenue_goals["monthly"].current,
            },
        }

    def _risk_assessment(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        risks = [
            {"category": "Market", "risk": "Traffic volatility", "score": 6, "mitigation": "Diversify channels"},
            {"category": "Operational", "risk": "Task queue saturation", "score": 4, "mitigation": "Scale workers"},
            {"category": "Financial", "risk": "Low conversion efficiency", "score": 5, "mitigation": "Optimize funnel"},
        ]
        high_priority = [r for r in risks if r["score"] >= 6]
        return {
            "risks_identified": len(risks),
            "high_priority_risks": high_priority,
            "overall_risk_score": round(sum(r["score"] for r in risks) / len(risks), 2),
        }

    def _coordinate_agents(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        task_description = input_data.get("task", "Collaborative objective")
        agent_ids = input_data.get("agents", ["researcher", "creator", "marketer"])
        collaboration_id = f"collab_{int(time.time())}"
        for agent_id in agent_ids:
            self.message_bus.create_task(
                task_type="collaborative",
                description=task_description,
                assigned_to=agent_id,
                priority=MessagePriority.HIGH,
                input_data={"collaboration_id": collaboration_id, "objective": task_description},
            )
        return {
            "collaboration_id": collaboration_id,
            "agents_coordinated": len(agent_ids),
        }

    def _optimize_revenue(self, _input_data: Dict[str, Any]) -> Dict[str, Any]:
        current = self.revenue_goals["monthly"].current
        initiatives = [
            {"area": "pricing", "action": "Review offer packaging", "impact_estimate": 800},
            {"area": "retention", "action": "Email reactivation flow", "impact_estimate": 500},
            {"area": "acquisition", "action": "Focus high-intent channels", "impact_estimate": 900},
        ]
        total_impact = sum(item["impact_estimate"] for item in initiatives)
        return {
            "current_monthly_revenue": current,
            "projected_monthly_revenue": current + total_impact,
            "initiatives": initiatives,
        }

    def _default_director(self, _input_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "completed", "message": "Director task completed"}

    def _assign_strategy_tasks(self, strategy: Dict[str, Any]):
        for focus in strategy.get("focus_areas", []):
            self.message_bus.create_task(
                task_type="strategy_execution",
                description=f"Execute: {focus['action']}",
                assigned_to=focus["agent"],
                priority=MessagePriority.HIGH,
                input_data={"focus_area": focus},
            )

    def _auto_approve(self, decision: Decision):
        # --- Guardrail Check ---
        if self.kill_switch:
            logger.warning(f"Kill Switch is ACTIVE. Blocking decision {decision.id}")
            decision.status = "blocked_by_killswitch"
            return

        # Reset daily budget if date changed
        if datetime.now().date() > self.last_budget_reset:
            self.daily_spend = 0.0
            self.last_budget_reset = datetime.now().date()

        if self.daily_spend + decision.estimated_cost > self.max_daily_budget:
            logger.warning(f"Daily budget exceeded! Blocking decision {decision.id}")
            decision.status = "blocked_by_budget"
            return
        # -----------------------

        decision.status = "approved"
        decision.decided_at = datetime.now()
        self.daily_spend += decision.estimated_cost
        self.completed_decisions.append(decision)
        if decision in self.pending_decisions:
            self.pending_decisions.remove(decision)

    def _agent_loop(self):
        self._update_revenue_tracking()
        self._check_pending_decisions()
        self._monitor_agent_health()

    def _update_revenue_tracking(self):
        today_results = self.memory.query(search_key="task_result:", limit=100)
        revenue_total = 0.0
        for entry in today_results:
            value = entry.value if isinstance(entry.value, dict) else {}
            result = value.get("result", {}) if isinstance(value, dict) else {}
            if isinstance(result, dict):
                revenue_total += float(result.get("revenue_generated", result.get("revenue", 0)) or 0)

        self.revenue_goals["daily"].update(revenue_total)
        self.revenue_goals["weekly"].update(revenue_total * 3)
        self.revenue_goals["monthly"].update(revenue_total * 12)

        self.memory.store_shared(
            "revenue_goals",
            {
                period: {
                    "target": goal.target,
                    "current": goal.current,
                    "progress": goal.progress,
                    "on_track": goal.on_track,
                }
                for period, goal in self.revenue_goals.items()
            },
            importance=0.9,
        )

    def _check_pending_decisions(self):
        for decision in self.pending_decisions[:]:
            if decision.estimated_impact > self.human_approval_limit:
                if self.on_approval_required:
                    self.on_approval_required(
                        {
                            "id": decision.id,
                            "subject": decision.description,
                            "estimated_impact": decision.estimated_impact,
                        }
                    )
            else:
                self._auto_approve(decision)

    def _monitor_agent_health(self):
        agent_status = self.message_bus.get_agent_status()
        for agent_id, status in agent_status.items():
            if status.get("status") == "offline" and self.on_alert:
                self.on_alert(f"Agent {agent_id} is offline", "warning")

    def receive_report(self, agent_id: str, report: Dict[str, Any]):
        self.memory.store_shared(f"report:{agent_id}:{int(time.time())}", report, importance=0.8)
        reported_revenue = float(report.get("revenue_generated", report.get("revenue", 0)) or 0)
        if reported_revenue:
            self.revenue_goals["daily"].update(self.revenue_goals["daily"].current + reported_revenue)

    def request_human_input(self, subject: str, details: Dict[str, Any], callback: Optional[Callable] = None):
        if self.on_approval_required:
            self.on_approval_required(
                {
                    "id": f"human_input_{int(time.time())}",
                    "subject": subject,
                    "details": details,
                    "callback": callback,
                }
            )

    def broadcast_directive(self, directive: str, data: Optional[Dict[str, Any]] = None):
        self.message_bus.send_broadcast(
            sender=self.agent_id,
            subject=directive,
            content=data or {},
            priority=MessagePriority.HIGH,
        )

    def get_dashboard_data(self) -> Dict[str, Any]:
        agents = self.message_bus.get_agent_status()
        return {
            "revenue": {
                "daily": self.revenue_goals["daily"].current,
                "daily_target": self.revenue_goals["daily"].target,
                "daily_progress": self.revenue_goals["daily"].progress,
                "weekly": self.revenue_goals["weekly"].current,
                "weekly_target": self.revenue_goals["weekly"].target,
                "monthly": self.revenue_goals["monthly"].current,
                "monthly_target": self.revenue_goals["monthly"].target,
            },
            "agents": {
                "total": len(agents),
                "online": len([a for a in agents.values() if a.get("status") == "online"]),
                "performance": agents,
            },
            "campaigns": {"active": len(self.active_campaigns)},
            "decisions": {"pending": len(self.pending_decisions), "completed": len(self.completed_decisions)},
            "alerts": self._get_active_alerts(),
        }

    def _get_active_alerts(self) -> List[Dict[str, Any]]:
        alerts = self.memory.retrieve("alerts", [])
        if not isinstance(alerts, list):
            return []
        now = datetime.now()
        filtered = []
        for alert in alerts[-20:]:
            timestamp = alert.get("timestamp")
            try:
                dt = datetime.fromisoformat(timestamp)
            except Exception:
                dt = now
            if now - dt <= timedelta(hours=24):
                filtered.append(alert)
        return filtered
