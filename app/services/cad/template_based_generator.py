"""
Template-Based CAD Generator
Sinh file CAD DXF dựa trên template có sẵn trong database
"""
import logging
from typing import List, Dict, Optional
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class TemplateBasedCADGenerator:
    """
    Generate CAD DXF commands từ template
    Template chứa layout chuẩn của tủ điện với placeholders
    """
    
    @staticmethod
    def generate_from_template(
        project_name: str,
        devices: List[Dict],
        enclosure_spec: Dict,
        templates: List[Dict]
    ) -> List[str]:
        """
        Generate DXF commands từ template
        
        Args:
            project_name: Tên dự án
            devices: Danh sách thiết bị
            enclosure_spec: Kích thước vỏ tủ
            templates: List of CAD templates từ DB
        
        Returns:
            List of DXF command strings
        """
        commands = []
        
        # Find best matching template
        template = TemplateBasedCADGenerator._select_best_template(
            templates, enclosure_spec, devices
        )
        
        if not template:
            logger.warning("No suitable CAD template found, using default generation")
            return TemplateBasedCADGenerator._generate_default_cad(
                project_name, devices, enclosure_spec
            )
        
        logger.info(
            f"Using CAD template: {template.get('name')}",
            extra={"template_id": template.get("id")}
        )
        
        # Extract template commands
        template_commands = template.get("commands", [])
        
        # Replace placeholders
        for cmd in template_commands:
            replaced = TemplateBasedCADGenerator._replace_placeholders(
                cmd, project_name, devices, enclosure_spec
            )
            commands.append(replaced)
        
        logger.info(
            f"Generated {len(commands)} CAD commands from template",
            extra={"command_count": len(commands)}
        )
        
        return commands
    
    @staticmethod
    def _select_best_template(
        templates: List[Dict],
        enclosure_spec: Dict,
        devices: List[Dict]
    ) -> Optional[Dict]:
        """
        Select template phù hợp nhất based on:
        - Enclosure size similarity
        - Device count similarity
        - Incomer rating match
        """
        if not templates:
            return None
        
        target_incomer = enclosure_spec.get("incomer_rating", 630)
        target_device_count = len(devices)
        
        best_template = None
        best_score = 0
        
        for template in templates:
            score = 0
            
            # Match incomer rating
            tpl_incomer = template.get("incomer_rating", 0)
            if tpl_incomer == target_incomer:
                score += 50
            elif abs(tpl_incomer - target_incomer) < 200:
                score += 30
            
            # Match device count
            tpl_device_count = template.get("device_count", 0)
            if abs(tpl_device_count - target_device_count) < 5:
                score += 30
            elif abs(tpl_device_count - target_device_count) < 10:
                score += 15
            
            # Prefer templates with similar enclosure size
            tpl_height = template.get("enclosure_height", 0)
            target_height = enclosure_spec.get("height", 0)
            if abs(tpl_height - target_height) < 200:
                score += 20
            
            if score > best_score:
                best_score = score
                best_template = template
        
        logger.info(
            f"Selected template with score: {best_score}",
            extra={"template_id": best_template.get("id") if best_template else None}
        )
        
        return best_template
    
    @staticmethod
    def _replace_placeholders(
        command: str,
        project_name: str,
        devices: List[Dict],
        enclosure_spec: Dict
    ) -> str:
        """
        Replace placeholders trong template command
        
        Placeholders:
        - {{PROJECT_NAME}} → project name
        - {{HEIGHT}} → enclosure height
        - {{WIDTH}} → enclosure width
        - {{DEPTH}} → enclosure depth
        - {{INCOMER_RATING}} → incomer current rating
        - {{DEVICE_COUNT}} → total device count
        - {{FEEDER_COUNT}} → number of feeders
        """
        replacements = {
            "{{PROJECT_NAME}}": project_name,
            "{{HEIGHT}}": str(enclosure_spec.get("height", 2000)),
            "{{WIDTH}}": str(enclosure_spec.get("width", 1000)),
            "{{DEPTH}}": str(enclosure_spec.get("depth", 600)),
            "{{INCOMER_RATING}}": str(enclosure_spec.get("incomer_rating", 630)),
            "{{DEVICE_COUNT}}": str(len(devices)),
            "{{FEEDER_COUNT}}": str(sum(1 for d in devices if d.get("section") == "Đầu ra")),
        }
        
        result = command
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        
        return result
    
    @staticmethod
    def _generate_default_cad(
        project_name: str,
        devices: List[Dict],
        enclosure_spec: Dict
    ) -> List[str]:
        """
        Generate basic CAD commands nếu không có template
        """
        commands = []
        
        height = enclosure_spec.get("height", 2000)
        width = enclosure_spec.get("width", 1000)
        depth = enclosure_spec.get("depth", 600)
        
        # Title block
        commands.append(f"; CAD FILE FOR {project_name}")
        commands.append(f"; Auto-generated by WebBaoGia BE_BOM")
        commands.append("")
        
        # Layer definitions
        commands.append("LAYER")
        commands.append("N")
        commands.append("ENCLOSURE")
        commands.append("C")
        commands.append("1")
        commands.append("")
        commands.append("")
        
        commands.append("LAYER")
        commands.append("N")
        commands.append("DEVICES")
        commands.append("C")
        commands.append("2")
        commands.append("")
        commands.append("")
        
        # Draw enclosure outline (rectangle)
        commands.append("LAYER")
        commands.append("S")
        commands.append("ENCLOSURE")
        commands.append("")
        
        commands.append("RECTANGLE")
        commands.append("0,0")
        commands.append(f"{width},{height}")
        commands.append("")
        
        # Add text annotation
        commands.append("LAYER")
        commands.append("S")
        commands.append("DEVICES")
        commands.append("")
        
        commands.append("TEXT")
        commands.append("50,50")
        commands.append("100")
        commands.append("0")
        commands.append(f"{project_name}")
        commands.append("")
        
        commands.append("TEXT")
        commands.append("50,150")
        commands.append("60")
        commands.append("0")
        commands.append(f"H{height}xW{width}xD{depth}")
        commands.append("")
        
        # Add device annotations (simple list)
        y_offset = 250
        for idx, device in enumerate(devices[:10]):  # Limit to 10 for simplicity
            device_text = f"{device.get('name', 'Device')} x{device.get('quantity', 1)}"
            commands.append("TEXT")
            commands.append(f"50,{y_offset + idx * 80}")
            commands.append("50")
            commands.append("0")
            commands.append(device_text)
            commands.append("")
        
        commands.append("ZOOM")
        commands.append("E")
        commands.append("")
        
        return commands
