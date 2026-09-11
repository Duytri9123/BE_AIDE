import networkx as nx
from dataclasses import dataclass
from app.core.config import settings


@dataclass
class ProtectionViolation:
    parent_id: str
    child_id: str
    rule: str
    expected: str
    actual: str
    severity: str

class ProtectionCheckService:
    @staticmethod
    def validate_hierarchy(graph: nx.DiGraph) -> list[ProtectionViolation]:
        """Kiểm tra các quy tắc bảo vệ thiết bị (Icu, In) trên cây đồ thị."""
        violations = []
        
        # Hệ số đồng thời K (cấu hình qua PROTECTION_SIMULTANEITY_FACTOR trong .env)
        k_simultaneity = settings.PROTECTION_SIMULTANEITY_FACTOR
        
        for node in graph.nodes():
            if node == "GRID":
                continue
                
            node_data = graph.nodes[node]
            children = list(graph.successors(node))
            
            if not children:
                continue
                
            in_parent = node_data.get("in_a", 0)
            icu_parent = node_data.get("icu_ka", 0)
            
            sum_in_children = 0
            
            for child in children:
                child_data = graph.nodes[child]
                in_child = child_data.get("in_a", 0)
                icu_child = child_data.get("icu_ka", 0)
                
                sum_in_children += in_child
                
                # Check 1: Icu(parent) >= Icu(child)
                if icu_child > icu_parent and icu_parent > 0:
                    violations.append(ProtectionViolation(
                        parent_id=node,
                        child_id=child,
                        rule="Cascading Icu",
                        expected=f"<={icu_parent}kA",
                        actual=f"{icu_child}kA",
                        severity="high"
                    ))
                    
            # Check 2: In(parent) >= sum(In(children)) * K_simultaneity
            required_in = sum_in_children * k_simultaneity
            if in_parent < required_in and in_parent > 0:
                violations.append(ProtectionViolation(
                    parent_id=node,
                    child_id="multiple",
                    rule="Current Capacity",
                    expected=f">={required_in}A",
                    actual=f"{in_parent}A",
                    severity="medium"
                ))
                
        return violations
