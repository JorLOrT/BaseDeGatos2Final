"""
routes/clientes.py - Endpoints de clientes
"""

from fastapi import APIRouter, HTTPException, Query
from services import ClientesService

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("")
def listar_clientes(limite: int = Query(10, ge=1, le=100)):
    """Lista todos los clientes con conteo de órdenes"""
    clientes = ClientesService.listar(limite)
    return {"total": len(clientes), "clientes": clientes}


@router.get("/{cliente_id}")
def obtener_cliente(cliente_id: int):
    """Obtiene un cliente con sus órdenes asociadas"""
    cliente = ClientesService.obtener_con_ordenes(cliente_id)
    
    if not cliente:
        raise HTTPException(status_code=404, detail=f"Cliente {cliente_id} no encontrado")
    
    return cliente
