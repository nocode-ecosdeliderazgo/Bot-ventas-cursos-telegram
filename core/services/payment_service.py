"""
Servicio para manejar información de pagos y datos bancarios.
"""

import logging
from typing import Dict, Optional
from core.services.database import DatabaseService

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self, db: DatabaseService):
        self.db = db

    async def get_payment_info(self) -> Optional[Dict]:
        """
        Obtiene la información de pago activa desde la base de datos.
        
        Returns:
            Dict con datos de pago o None si no hay datos activos
        """
        try:
            query = """
            SELECT 
                company_name,
                bank_name,
                clabe_account,
                rfc,
                cfdi_usage,
                cfdi_description
            FROM payment_info 
            WHERE is_active = true 
            ORDER BY created_at DESC 
            LIMIT 1
            """
            
            result = await self.db.fetch_one(query)
            
            if result:
                logger.info("✅ Información de pago obtenida correctamente")
                return dict(result)
            else:
                logger.warning("⚠️ No se encontró información de pago activa")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo información de pago: {e}")
            return None

    def format_payment_message(self, payment_data: Dict) -> str:
        """
        Formatea los datos de pago en un mensaje elegante para Telegram.
        
        Args:
            payment_data: Diccionario con datos de pago
            
        Returns:
            Mensaje formateado con datos bancarios
        """
        if not payment_data:
            return "❌ Error: No se pudo obtener la información de pago. Contacta a soporte."

        try:
            message = f"""💳 **DATOS PARA REALIZAR TU PAGO**

🏢 **Razón Social:** {payment_data.get('company_name', 'N/A')}
🏦 **Banco:** {payment_data.get('bank_name', 'N/A')}
💳 **Cuenta CLABE:** `{payment_data.get('clabe_account', 'N/A')}`
📄 **RFC:** {payment_data.get('rfc', 'N/A')}
📋 **Uso de CFDI:** {payment_data.get('cfdi_usage', 'N/A')} - {payment_data.get('cfdi_description', 'N/A')}

📲 *Envía tu comprobante de pago al asesor para confirmar tu inscripción inmediatamente.*

🚀 **¡Te conectaré con un asesor ahora mismo!**"""

            logger.info("✅ Mensaje de pago formateado correctamente")
            return message
            
        except Exception as e:
            logger.error(f"❌ Error formateando mensaje de pago: {e}")
            return "❌ Error generando información de pago. Contacta a soporte."

    async def get_formatted_payment_info(self) -> str:
        """
        Método de conveniencia que obtiene y formatea la información de pago.
        
        Returns:
            Mensaje formateado listo para enviar
        """
        payment_data = await self.get_payment_info()
        return self.format_payment_message(payment_data) 