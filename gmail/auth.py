# -*- coding: utf-8 -*-
"""
AUTENTICACIÓN GMAIL - MÓDULO IMAP
Gestión de facturas - TASCA BAREA S.L.L.
"""

import imaplib
import email as email_lib
from email.header import decode_header
from email.message import Message
from typing import Optional
import ssl

try:
    from gmail.gmail_config import (
    GMAIL_EMAIL,
    GMAIL_IMAP_SERVER,
    GMAIL_IMAP_PORT,
    ETIQUETA_ENTRADA,
    ETIQUETA_PROCESADO
)
except ImportError:
    from gmail_config import (
    GMAIL_EMAIL,
    GMAIL_IMAP_SERVER,
    GMAIL_IMAP_PORT,
    ETIQUETA_ENTRADA,
    ETIQUETA_PROCESADO
)
from config_local import GMAIL_APP_PASSWORD, verificar_credenciales


class GmailConnection:
    """Gestiona la conexión IMAP con Gmail."""
    
    def __init__(self):
        self.mail: Optional[imaplib.IMAP4_SSL] = None
        self.conectado = False
    
    def conectar(self) -> tuple[bool, str]:
        """
        Establece conexión con Gmail.
        
        Returns:
            Tuple (éxito, mensaje)
        """
        # Verificar credenciales
        if not verificar_credenciales():
            return False, "Credenciales no configuradas"
        
        try:
            # Crear conexión SSL
            context = ssl.create_default_context()
            self.mail = imaplib.IMAP4_SSL(
                GMAIL_IMAP_SERVER, 
                GMAIL_IMAP_PORT,
                ssl_context=context
            )
            
            # Login
            self.mail.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD.replace(" ", ""))
            
            self.conectado = True
            return True, f"Conectado a {GMAIL_EMAIL}"
            
        except imaplib.IMAP4.error as e:
            return False, f"Error de autenticación: {e}"
        except Exception as e:
            return False, f"Error de conexión: {e}"
    
    def desconectar(self):
        """Cierra la conexión con Gmail."""
        if self.mail and self.conectado:
            try:
                self.mail.logout()
            except Exception:
                pass
            self.conectado = False
    
    def seleccionar_etiqueta(self, etiqueta: str = None) -> tuple[bool, int]:
        """
        Selecciona una etiqueta/carpeta de Gmail.
        
        Args:
            etiqueta: Nombre de la etiqueta (default: FACTURAS)
        
        Returns:
            Tuple (éxito, número_de_mensajes)
        """
        if not self.conectado:
            return False, 0
        
        etiqueta = etiqueta or ETIQUETA_ENTRADA
        
        try:
            # En Gmail, las etiquetas se acceden así
            status, data = self.mail.select(etiqueta)
            
            if status == 'OK':
                num_mensajes = int(data[0])
                return True, num_mensajes
            else:
                return False, 0
                
        except Exception as e:
            print(f"Error seleccionando etiqueta {etiqueta}: {e}")
            return False, 0
    
    def obtener_ids_emails(self, solo_sin_leer: bool = False, desde_fecha: str = None) -> list[bytes]:
        """
        Obtiene los IDs de emails en la etiqueta seleccionada.
        
        Args:
            solo_sin_leer: Si True, solo devuelve emails no leídos (UNSEEN)
            desde_fecha: Fecha mínima en formato "DD-Mon-YYYY" (ej: "01-Jan-2026")
        
        Returns:
            Lista de IDs de emails
        """
        if not self.conectado:
            return []
        
        try:
            # Construir filtro
            filtros = []
            
            if solo_sin_leer:
                filtros.append("UNSEEN")
            
            if desde_fecha:
                filtros.append(f'SINCE "{desde_fecha}"')
            
            if filtros:
                filtro = "(" + " ".join(filtros) + ")"
            else:
                filtro = "ALL"
            
            status, messages = self.mail.search(None, filtro)
            if status == 'OK':
                ids = messages[0].split()
                return ids
            return []
        except Exception as e:
            print(f"Error obteniendo IDs: {e}")
            return []
    
    def obtener_email(self, email_id: bytes) -> Optional[Message]:
        """
        Descarga un email completo por su ID.
        
        Args:
            email_id: ID del email
        
        Returns:
            Objeto Message o None si error
        """
        if not self.conectado:
            return None
        
        try:
            status, data = self.mail.fetch(email_id, "(RFC822)")
            
            if status == 'OK':
                raw_email = data[0][1]
                msg = email_lib.message_from_bytes(raw_email)
                return msg
            return None
            
        except Exception as e:
            print(f"Error descargando email {email_id}: {e}")
            return None
    
    def obtener_mensaje_id_gmail(self, email_id: bytes) -> Optional[str]:
        """
        Obtiene el Message-ID único de Gmail.
        
        Args:
            email_id: ID secuencial del email
        
        Returns:
            Message-ID único o None
        """
        if not self.conectado:
            return None
        
        try:
            # Obtener el X-GM-MSGID (ID único de Gmail)
            status, data = self.mail.fetch(email_id, "(X-GM-MSGID)")
            if status == 'OK':
                # Parsear respuesta
                response = data[0].decode() if isinstance(data[0], bytes) else str(data[0])
                # Extraer el ID
                import re
                match = re.search(r'X-GM-MSGID\s+(\d+)', response)
                if match:
                    return match.group(1)
            
            # Fallback: usar Message-ID del header
            msg = self.obtener_email(email_id)
            if msg:
                return msg.get("Message-ID", str(email_id))
            
            return str(email_id)
            
        except Exception as e:
            print(f"Error obteniendo Message-ID: {e}")
            return str(email_id)
    
    def mover_a_procesadas(self, email_id: bytes) -> bool:
        """
        Mueve un email de FACTURAS a FACTURAS_PROCESADAS.
        
        Args:
            email_id: ID del email
        
        Returns:
            True si éxito
        """
        if not self.conectado:
            return False
        
        try:
            # Añadir etiqueta FACTURAS_PROCESADAS
            self.mail.store(email_id, '+X-GM-LABELS', ETIQUETA_PROCESADO)
            
            # Quitar etiqueta FACTURAS
            self.mail.store(email_id, '-X-GM-LABELS', ETIQUETA_ENTRADA)
            
            return True
            
        except Exception as e:
            print(f"Error moviendo email: {e}")
            return False
    
    def __enter__(self):
        """Context manager - entrada."""
        self.conectar()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager - salida."""
        self.desconectar()


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def decodificar_header(header: str) -> str:
    """
    Decodifica un header de email (puede tener encoding especial).
    
    Args:
        header: Header crudo del email
    
    Returns:
        String decodificado
    """
    if not header:
        return ""
    
    decoded_parts = decode_header(header)
    result = []
    
    for content, charset in decoded_parts:
        if isinstance(content, bytes):
            try:
                if charset:
                    result.append(content.decode(charset))
                else:
                    result.append(content.decode('utf-8', errors='replace'))
            except (UnicodeDecodeError, LookupError):
                result.append(content.decode('latin-1', errors='replace'))
        else:
            result.append(str(content))
    
    return ''.join(result)


def extraer_info_email(msg: Message) -> dict:
    """
    Extrae información básica de un email.
    
    Args:
        msg: Objeto Message
    
    Returns:
        Dict con de, asunto, fecha
    """
    return {
        'de': decodificar_header(msg.get("From", "")),
        'asunto': decodificar_header(msg.get("Subject", "")),
        'fecha': msg.get("Date", ""),
        'message_id': msg.get("Message-ID", ""),
    }


def obtener_adjuntos(msg: Message) -> list[dict]:
    """
    Extrae información de adjuntos de un email.
    
    Args:
        msg: Objeto Message
    
    Returns:
        Lista de dicts con info de adjuntos
    """
    adjuntos = []
    
    if msg.is_multipart():
        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition", ""))
            
            if "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    filename = decodificar_header(filename)
                    content_type = part.get_content_type()
                    data = part.get_payload(decode=True)
                    
                    adjuntos.append({
                        'nombre': filename,
                        'tipo': content_type,
                        'tamaño': len(data) if data else 0,
                        'datos': data
                    })
    
    return adjuntos


# =============================================================================
# TEST DE CONEXIÓN
# =============================================================================

def test_conexion():
    """Prueba la conexión a Gmail."""
    print("=" * 60)
    print("TEST DE CONEXIÓN GMAIL")
    print("=" * 60)
    
    print(f"\nCuenta: {GMAIL_EMAIL}")
    print(f"Servidor: {GMAIL_IMAP_SERVER}:{GMAIL_IMAP_PORT}")
    
    # Verificar credenciales
    print("\n1. Verificando credenciales...")
    if not verificar_credenciales():
        return False
    print("   ✅ Credenciales configuradas")
    
    # Conectar
    print("\n2. Conectando a Gmail...")
    gmail = GmailConnection()
    exito, mensaje = gmail.conectar()
    
    if not exito:
        print(f"   ❌ {mensaje}")
        return False
    print(f"   ✅ {mensaje}")
    
    # Seleccionar etiqueta FACTURAS
    print(f"\n3. Seleccionando etiqueta '{ETIQUETA_ENTRADA}'...")
    exito, num_emails = gmail.seleccionar_etiqueta(ETIQUETA_ENTRADA)
    
    if not exito:
        print(f"   ❌ No se pudo seleccionar la etiqueta")
        print(f"   Verifica que existe la etiqueta '{ETIQUETA_ENTRADA}' en Gmail")
        gmail.desconectar()
        return False
    
    print(f"   ✅ Etiqueta seleccionada: {num_emails} emails en total")
    
    # Contar con filtro de fecha (desde 1 enero 2026)
    desde_fecha = "01-Jan-2026"
    ids_desde_fecha = gmail.obtener_ids_emails(solo_sin_leer=False, desde_fecha=desde_fecha)
    ids_todos = gmail.obtener_ids_emails(solo_sin_leer=False, desde_fecha=None)
    
    print(f"   📬 Total en FACTURAS: {len(ids_todos)}")
    print(f"   📩 Desde {desde_fecha}: {len(ids_desde_fecha)}")
    print(f"   📭 Anteriores (ignorar): {len(ids_todos) - len(ids_desde_fecha)}")
    
    # Mostrar primeros emails desde fecha (si hay)
    if len(ids_desde_fecha) > 0:
        print(f"\n4. Listando primeros emails desde {desde_fecha} (máx. 5)...")
        
        for i, email_id in enumerate(ids_desde_fecha[:5]):
            msg = gmail.obtener_email(email_id)
            if msg:
                info = extraer_info_email(msg)
                adjuntos = obtener_adjuntos(msg)
                print(f"\n   [{i+1}] De: {info['de'][:50]}...")
                print(f"       Asunto: {info['asunto'][:50]}...")
                print(f"       Adjuntos: {len(adjuntos)}")
                for adj in adjuntos:
                    print(f"         - {adj['nombre']} ({adj['tamaño']} bytes)")
    
    # Desconectar
    print("\n5. Desconectando...")
    gmail.desconectar()
    print("   ✅ Desconectado")
    
    print("\n" + "=" * 60)
    print("✅ TEST COMPLETADO CORRECTAMENTE")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    test_conexion()
