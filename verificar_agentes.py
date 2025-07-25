"""
Script para verificar las importaciones de agentes.
"""

print("Verificando importaciones de agentes...")

try:
    print("Importando conversation_processor...")
    from core.agents.conversation_processor import ConversationProcessor
    print("ConversationProcessor importado correctamente")
except Exception as e:
    print(f"Error importando ConversationProcessor: {e}")

try:
    print("Importando intelligent_sales_agent...")
    from core.agents.intelligent_sales_agent import IntelligentSalesAgent
    print("IntelligentSalesAgent importado correctamente")
except Exception as e:
    print(f"Error importando IntelligentSalesAgent: {e}")

try:
    print("Importando agent_tools...")
    from core.agents.agent_tools import AgentTools
    print("AgentTools importado correctamente")
except Exception as e:
    print(f"Error importando AgentTools: {e}")

try:
    print("Importando smart_sales_agent...")
    from core.agents.smart_sales_agent import SmartSalesAgent
    print("SmartSalesAgent importado correctamente")
except Exception as e:
    print(f"Error importando SmartSalesAgent: {e}")

print("Verificación de importaciones completada.")
