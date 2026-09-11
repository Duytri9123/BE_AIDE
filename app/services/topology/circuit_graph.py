import networkx as nx

class CircuitGraphService:
    @staticmethod
    def build_graph(devices: list[dict]) -> nx.DiGraph:
        """Tạo đồ thị có hướng từ danh sách thiết bị có phân cấp."""
        G = nx.DiGraph()
        G.add_node("GRID", type="source")
        
        for dev in devices:
            dev_id = dev.get("id", str(id(dev)))
            parent_id = dev.get("parent_id")
            G.add_node(dev_id, **dev)
            
            if parent_id:
                G.add_edge(parent_id, dev_id)
            elif dev.get("is_incomer"):
                G.add_edge("GRID", dev_id)
                
        return G

    @staticmethod
    def to_json(graph: nx.DiGraph) -> dict:
        """Serialize đồ thị thành dạng JSON nodes/edges."""
        return nx.node_link_data(graph)

    @staticmethod
    def get_device_depth(graph: nx.DiGraph, device_id: str) -> int:
        """Tính chiều sâu của thiết bị tính từ nguồn (GRID)."""
        try:
            return nx.shortest_path_length(graph, "GRID", device_id)
        except nx.NetworkXNoPath:
            return -1

    @staticmethod
    def get_downstream_devices(graph: nx.DiGraph, device_id: str) -> list:
        """Lấy tất cả các thiết bị nằm sau thiết bị chỉ định."""
        return list(nx.descendants(graph, device_id))
