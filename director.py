"""
MAMS - Matrix Agentic Money System
Director Agent (CEO) - Orchestrates all other agents
"""

import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from base_agent import BaseAgent, AgentCapability, AgentStatus, MessagePriority
from message_bus import MessageType, Message, MessageBus, get_message_bus
from memory import MemoryType, SharedMemory, get_memory
from config import get_config
import loguru

logger = loguru.logger


@dataclass
class RevenueGoal:
    """Revenue goal tracking"""
    target: float
    current: float
    period: str
    progress: float = 0
    on_track: bool = False
    
    def update(self, current: float):
        self.current = current
        self.progress = (current / self.target * 100) if self.target > 0 else 0
        self.on_track = self.progress >= 50


@dataclass
class Decision:
    """Agent decision record"""
    id: str
    decision_type: str
    description: str
    agents_involved: List[str]
    estimated_impact: float
    status: str  # pending, approved, rejected, implemented
    created_at: datetime
    decided_at: Optional[datetime] = None
    result: Optional[Dict] = None


class DirectorAgent(BaseAgent):
    """
    Director Agent - The CEO of the agent system.
    Coordinates all agents, makes strategic decisions, and manages the overall operation.
    """
    
    def __init__(self, config: Dict = None):
        super().__init__(
            agent_id="director",
            agent_type="director",
            name="Director Agent (CEO)",
            description="Chief Executive Orchestrator - Coordinates all agents and manages operations",
            capabilities=[
                AgentCapability.ANALYZE_DATA,
                AgentCapability.COMMUNICATION,
            ],
            config=config or {},
        )
        
        self.memory = get_memory()
        self.message_bus = get_message_bus()
        
        # Strategic state
        self.current_strategy: Dict = {}
        self.active_campaigns: List[str] = []
        self.pending_decisions: List[Decision] = []
        self.completed_decisions: List[Decision] = []
        
        # Revenue tracking
        self.revenue_goals: Dict[str, RevenueGoal] = {
            "daily": RevenueGoal(target=333, current=0, period="daily"),
            "weekly": RevenueGoal(target=2333, current=0, period="weekly"),
            "monthly": RevenueGoal(target=10000, current=0, period="monthly"),
        }
        
        # Agent registry
        self.registered_agents: Dict[str, Dict] = {}
        
        # Decision thresholds
        self.auto_approval_limit = config.get("auto_approval_limit", 100) if config else 100
        self.human_approval_limit = config.get("human_approval_limit", 1000) if config else 1000
        
        # Callbacks for human interaction
        self.on_approval_required: Optional[Callable] = None
        self.on_alert: Optional[Callable] = None
        
        logger.info("Director Agent (CEO) initialized")
    
    def execute_task(self, task_type: str, description: str, input_data: Dict) -> Dict:
        """Execute director task"""
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
        return handler(input_data)
    
    def _strategic_planning(self, input_data: Dict) -> Dict:
        """Develop strategic plan"""
        market_data = input_data.get("market_data", {})
        current_state = input_data.get("current_state", {})
        
        # Analyze current position
        strengths = current_state.get("strengths", ["content_creation", "automation"])
        weaknesses = current_state.get("weaknesses", ["paid_traffic", "conversion"])
        opportunities = market_data.get("opportunities", [])
        
        # Develop strategy
        strategy = {
            "id": f"strategy_{int(time.time())}",
            "name": "Q2 Growth Strategy",
            "horizon": "90 days",
            "north_star_metric": "revenue",
            "focus_areas": [
                {
                    "area": "content_scale",
                    "action": "Increase content production by 50%",
                    "agent": "creator",
                    "kpi": "articles_per_week",
                    "target": 20,
                },
                {
                    "area": "traffic_diversification",
                    "action": "Reduce organic dependency, grow paid channels",
                    "agent": "marketer",
                    "kpi": "paid_traffic_percentage",
                    "target": 30,
                },
                {
                    "area": "conversion_optimization",
                    "action": "Improve overall conversion by 25%",
                    "agent": "sales",
                    "kpi": "conversion_rate",
                    "target": 3.5,
                },
            ],
            "budget_allocation": {
                "content": 0.3,
                "marketing": 0.4,
                "tools": 0.2,
                "reserve": 0.1,
            },
            "milestones": [
                {"week": 4, "goal": "Launch 3 new content verticals"},
                {"week": 8, "goal": "Achieve 20% paid traffic"},
                {"week": 12, "goal": "Hit $15K monthly revenue"},
            ],
            "risks": [
                {"risk": "Algorithm changes", "mitigation": "Diversify traffic sources"},
                {"risk": "Competition increase", "mitigation": "Focus on unique value"},
            ],
            "created_at": datetime.now().isoformat(),
        }
        
        self.current_strategy = strategy
        self.memory.store_shared("current_strategy", strategy)
        
        # Assign tasks to agents
        self._assign_strategy_tasks(strategy)
        
        return {
            "strategy_id": strategy["id"],
            "focus_areas": len(strategy["focus_areas"]),
            "estimated_impact": "High",
            "tasks_created": len(strategy["focus_areas"]),
        }
    
    def _resource_allocation(self, input_data: Dict) -> Dict:
        """Allocate resources to agents"""
        priorities = input_data.get("priorities", [])
        total_budget = input_data.get("budget", 500)
        
        # Allocate based on priorities
        allocation = {}
        remaining = total_budget
        
        for i, priority in enumerate(priorities):
            share = total_budget * (0.4 if i == 0 else 0.2)
            allocation[priority["agent"]] = {
                "amount": share,
                "tasks": priority.get("tasks", []),
                "expected_output": priority.get("expected_output", ""),
            }
            remaining -= share
        
        if remaining > 0:
            allocation["reserve"] = {"amount": remaining}
        
        return {
            "allocation": allocation,
            "total_budget": total_budget,
            "efficiency_score": random.uniform(75, 95),
        }
    
    def _evaluate_opportunity(self, input_data: Dict) -> Dict:
        """Evaluate a business opportunity"""
        opportunity = input_data.get("opportunity", {})
        
        # Score the opportunity
        scores = {
            "market_size": random.randint(1, 10),
            "competition": random.randint(1, 10),
            "timing": random.randint(1, 10),
            "resources_available": random.randint(1, 10),
            "monetization_potential": random.randint(1, 10),
        }
        
        overall_score = sum(scores.values()) / len(scores)
        
        decision = {
            "id": f"opp_{int(time.time())}",
            "opportunity": opportunity,
            "scores": scores,
            "overall_score": overall_score,
            "decision": "pursue" if overall_score >= 6 else "defer",
            "recommended_actions": [
                "Assign to researcher for deep dive",
                "Quick MVP test",
                "Evaluate competitor response",
            ],
        }
        
        # Store decision
        self.pending_decisions.append(Decision(
            id=decision["id"],
            decision_type="opportunity",
            description=str(opportunity),
            agents_involved=["researcher", "creator"],
            estimated_impact=random.uniform(1000, 50000),
            status="pending",
            created_at=datetime.now(),
        ))
        
        # Auto-approve if high score and low cost
        if overall_score >= 7:
            self._auto_approve(decision)
        
        return decision
    
    def _orchestrate_campaign(self, input_data: Dict) -> Dict:
        """Orchestrate a full marketing campaign"""
        campaign_name = input_data.get("name", "Campaign")
        channels = input_data.get("channels", ["seo", "social", "email"])
        budget = input_data.get("budget", 500)
        
        campaign_id = f"campaign_{int(time.time())}"
        
        # Create campaign phases
        phases = [
            {
                "phase": 1,
                "name": "Research & Planning",
                "agents": ["researcher"],
                "tasks": ["keyword_research", "competitor_analysis"],
                "duration_hours": 4,
            },
            {
                "phase": 2,
                "name": "Content Creation",
                "agents": ["creator"],
                "tasks": ["create_blog_posts", "social_content", "email_sequence"],
                "duration_hours": 24,
            },
            {
                "phase": 3,
                "name": "Distribution",
                "agents": ["marketer"],
                "tasks": ["seo_optimization", "social_distribution", "email_campaign"],
                "duration_hours": 48,
            },
            {
                "phase": 4,
                "name": "Optimization",
                "agents": ["analyst", "sales"],
                "tasks": ["performance_tracking", "conversion_optimization"],
                "duration_hours": 72,
            },
        ]
        
        # Assign tasks
        for phase in phases:
            for agent_id in phase["agents"]:
                for task in phase["tasks"]:
                    self.message_bus.create_task(
                        task_type=task,
                        description=f"Campaign {campaign_name}: {task}",
                        assigned_to=agent_id,
                        priority=MessagePriority.NORMAL,
                        input_data={"campaign_id": campaign_id, "budget": budget / len(channels)},
                        metadata={"campaign_id": campaign_id, "phase": phase["phase"]},
                    )
        
        self.active_campaigns.append(campaign_id)
        
        return {
            "campaign_id": campaign_id,
            "name": campaign_name,
            "phases": len(phases),
            "estimated_duration": f"{sum(p['duration_hours'] for p in phases)} hours",
            "estimated_reach": random.randint(10000, 100000),
            "projected_roi": f"{random.randint(100, 300)}%",
        }
    
    def _performance_review(self, input_data: Dict) -> Dict:
        """Review system performance"""
        period = input_data.get("period", "weekly")
        
        # Get metrics from memory
        trends = self.memory.retrieve("trending_topics", [])
        campaigns = self.active_campaigns
        
        review = {
            "period": period,
            "date_range": {
                "start": (datetime.now() - timedelta(days=7)).isoformat(),
                "end": datetime.now().isoformat(),
            },
            "agent_performance": self._get_agent_performance(),
            "revenue_progress": {
                "daily": self.revenue_goals["daily"].progress,
                "weekly": self.revenue_goals["weekly"].progress,
                "monthly": self.revenue_goals["monthly"].progress,
            },
            "campaign_status": {
                "active": len(campaigns),
                "completed": random.randint(0, 5),
                "paused": random.randint(0, 2),
            },
            "content_production": {
                "created": random.randint(10, 50),
                "published": random.randint(5, 40),
                "pending_review": random.randint(0, 5),
            },
            "key_insights": [
                "Content volume up 20%",
                "Conversion rate stable at 2.5%",
                "Paid traffic showing strong ROI",
            ],
            "action_items": [
                "Scale high-performing content topics",
                "Pause underperforming campaigns",
                "Increase email capture rate",
            ],
        }
        
        self.memory.store_shared(f"performance_review:{period}", review)
        
        return review
    
    def _risk_assessment(self, input_data: Dict) -> Dict:
        """Assess operational risks"""
        risks = [
            {
                "category": "Market",
                "risk": "Algorithm changes affecting organic traffic",
                "likelihood": "medium",
                "impact": "high",
                "score": 6,
                "mitigation": "Diversify to paid channels",
            },
            {
                "category": "Operational",
                "risk": "Agent task queue backup",
                "likelihood": "low",
                "impact": "medium",
                "score": 3,
                "mitigation": "Monitor and scale agents",
            },
            {
                "category": "Financial",
                "risk": "Ad spend exceeds returns",
                "likelihood": "medium",
                "impact": "high",
                "score": 6,
                "mitigation": "Daily budget caps and ROAS monitoring",
            },
        ]
        
        return {
            "risks_identified": len(risks),
            "high_priority_risks": [r for r in risks if r["score"] >= 6],
            "risk_matrix": risks,
            "overall_risk_score": round(sum(r["score"] for r in risks) / len(risks), 1),
            "recommendations": [r["mitigation"] for r in risks],
        }
    
    def _coordinate_agents(self, input_data: Dict) -> Dict:
        """Coordinate multiple agents on a task"""
        task_description = input_data.get("task", "")
        agent_ids = input_data.get("agents", [])
        
        # Create collaborative task
        task_id = f"collab_{int(time.time())}"
        
        results = {}
        for agent_id in agent_ids:
            self.message_bus.create_task(
                task_type="collaborative",
                description=f"Collaborative: {task_description}",
                assigned_to=agent_id,
                priority=MessagePriority.HIGH,
                input_data={"collaboration_id": task_id},
                metadata={"collaboration": True, "agents": agent_ids},
            )
            results[agent_id] = {"status": "task_assigned"}
        
        return {
            "collaboration_id": task_id,
            "agents_coordinated": len(agent_ids),
            "tasks_created": len(agent_ids),
            "status": "in_progress",
        }
    
    def _optimize_revenue(self, input_data: Dict) -> Dict:
        """Optimize revenue generation"""
        current_revenue = self.revenue_goals["monthly"].current
        
        optimizations = [
            {
                "area": "affiliate_commissions",
                "action": "Negotiate higher commission rates",
                "potential_increase": 500,
                "effort": "medium",
            },
            {
                "area": "conversion_rate",
                "action": "A/B test pricing page",
                "potential_increase": 1000,
                "effort": "low",
            },
            {
                "area": "upsells",
                "action": "Implement order bumps",
                "potential_increase": 750,
                "effort": "medium",
            },
            {
                "area": "email_revenue",
                "action": "Launch re-engagement campaign",
                "potential_increase": 400,
                "effort": "low",
            },
        ]
        
        total_potential = sum(o["potential_increase"] for o in optimizations)
        
        return {
            "current_monthly_revenue": current_revenue,
            "optimizations_identified": len(optimizations),
            "optimizations": optimizations,
            "total_potential_increase": total_potential,
            "projected_monthly_revenue": current_revenue + total_potential,
            "recommended_immediate_actions": [optimizations[0], optimizations[1]],
        }
    
    def _default_director(self, input_data: Dict) -> Dict:
        """Default director handler"""
        return {"status": "completed", "message": "Director task completed"}
    
    def _get_agent_performance(self) -> Dict:
        """Get performance of all registered agents"""
        performance = {}
        for agent_id, info in self.registered_agents.items():
            performance[agent_id] = {
                "status": info.get("status", "unknown"),
                "tasks_completed": info.get("tasks_completed", 0),
                "avg_task_time": info.get("avg_task_time", 0),
                "health_score": random.randint(80, 100),
            }
        return performance
    
    def _assign_strategy_tasks(self, strategy: Dict):
        """Assign tasks from strategy to agents"""
        for focus in strategy["focus_areas"]:
            agent_id = focus["agent"]
            self.message_bus.create_task(
                task_type="strategy_execution",
                description=f"Strategy: {focus['action']}",
                assigned_to=agent_id,
                priority=MessagePriority.HIGH,
                input_data={"focus_area": focus},
            )
    
    def _auto_approve(self, decision: Dict):
        """Auto-approve decisions under threshold"""
        if decision.get("estimated_impact", 0) <= self.auto_approval_limit:
            decision["status"] = "approved"
            decision["decided_at"] = datetime.now()
            self._implement_decision(decision)
            logger.info(f"Auto-approved: {decision['id']}")
    
    def _implement_decision(self, decision: Dict):
        """Implement an approved decision"""
        # Create tasks for agents
        for agent_id in decision.get("agents_involved", []):
            self.message_bus.create_task(
                task_type="implement_decision",
                description=f"Decision: {decision['description']}",
                assigned_to=agent_id,
                priority=MessagePriority.NORMAL,
                input_data={"decision": decision},
            )
    
    def _agent_loop(self):
        """Director's periodic activities"""
        # Update revenue tracking
        self._update_revenue_tracking()
        
        # Check for pending decisions
        self._check_pending_decisions()
        
        # Monitor agent health
        self._monitor_agent_health()
        
        # Check for opportunities
        self._check_opportunities()
    
    def _update_revenue_tracking(self):
        """Update revenue goals with latest data"""
        # In production, would pull from actual sales data
        for goal in self.revenue_goals.values():
            # Simulate current revenue
            goal.update(goal.current + random.uniform(0, 50))
        
        # Store in memory
        self.memory.store_shared("revenue_goals", {
            k: {
                "target": v.target,
                "current": v.current,
                "progress": v.progress,
                "on_track": v.on_track,
            }
            for k, v in self.revenue_goals.items()
        })
    
    def _check_pending_decisions(self):
        """Check and process pending decisions"""
        for decision in self.pending_decisions[:]:
            if decision.status == "pending":
                # Check if needs human approval
                if decision.estimated_impact > self.human_approval_limit:
                    if self.on_approval_required:
                        self.on_approval_required(decision)
                else:
                    self._auto_approve({
                        "id": decision.id,
                        "agents_involved": decision.agents_involved,
                        "estimated_impact": decision.estimated_impact,
                    })
                    decision.status = "approved"
                    decision.decided_at = datetime.now()
                    self.completed_decisions.append(decision)
                    self.pending_decisions.remove(decision)
    
    def _monitor_agent_health(self):
        """Monitor health of all agents"""
        agent_status = self.message_bus.get_agent_status()
        
        for agent_id, status in agent_status.items():
            if status.get("status") == "offline":
                # Alert
                if self.on_alert:
                    self.on_alert(f"Agent {agent_id} is offline", "warning")
    
    def _check_opportunities(self):
        """Check for new opportunities"""
        # Check research agent for trending topics
        trending = self.memory.retrieve("trending_topics", [])
        
        if trending and isinstance(trending, list) and len(trending) > 0:
            top_trend = trending[0] if isinstance(trending[0], dict) else {"keyword": str(trending[0])}
            
            # If high-value opportunity
            if top_trend.get("score", 0) > 80:
                self._evaluate_opportunity({
                    "opportunity": top_trend,
                    "source": "trending",
                })
    
    def receive_report(self, agent_id: str, report: Dict):
        """Receive report from an agent"""
        self.memory.store_shared(f"report:{agent_id}:{int(time.time())}", report)
        
        # Process report
        if "revenue" in report:
            self.revenue_goals["daily"].update(
                self.revenue_goals["daily"].current + report.get("revenue", 0)
            )
        
        logger.info(f"Report received from {agent_id}")
    
    def request_human_input(self, subject: str, details: Dict, callback: Callable = None):
        """Request human input for critical decisions"""
        if self.on_approval_required:
            self.on_approval_required({
                "id": f"human_input_{int(time.time())}",
                "subject": subject,
                "details": details,
                "callback": callback,
            })
    
    def broadcast_directive(self, directive: str, data: Dict = None):
        """Broadcast a directive to all agents"""
        self.message_bus.send_broadcast(
            sender=self.agent_id,
            subject=directive,
            content=data or {},
            priority=MessagePriority.HIGH,
        )
    
    def get_dashboard_data(self) -> Dict:
        """Get data for dashboard display"""
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
                "total": len(self.registered_agents),
                "online": len([a for a in self.registered_agents.values() if a.get("status") == "online"]),
                "performance": self._get_agent_performance(),
            },
            "campaigns": {
                "active": len(self.active_campaigns),
            },
            "decisions": {
                "pending": len(self.pending_decisions),
                "completed_today": len(self.completed_decisions),
            },
            "alerts": self._get_active_alerts(),
        }
    
    def _get_active_alerts(self) -> List[Dict]:
        """Get active alerts"""
        alerts = []
        
        # Check revenue goals
        for period, goal in self.revenue_goals.items():
            if goal.progress < 25 and goal.current > 0:
                alerts.append({
                    "type": "revenue",
                    "severity": "warning",
                    "message": f"{period} revenue below target",
                    "progress": goal.progress,
                })
        
        return alerts


# Add random import
import random
