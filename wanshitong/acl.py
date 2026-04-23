"""Access control helpers."""

from __future__ import annotations

from wanshitong.model import Categoria, Documento, PermisoDocumento, Usuario, database


def puede_acceder_categoria(categoria: Categoria | None, usuario: Usuario) -> bool:
    """Return True when the user can access a category."""
    if usuario.tipo == "admin":
        return True
    if categoria is None:
        return False

    if not categoria.grupos:
        return False

    grupo_ids = {g.id for g in usuario.grupos}
    return any(grupo.id in grupo_ids for grupo in categoria.grupos)


def puede_leer(doc: Documento, usuario: Usuario) -> bool:
    """Return True if the user can read the document."""
    if usuario.tipo == "admin":
        return True
    if doc.autor_id == usuario.id:
        return True
    if doc.visibilidad == "publico" and doc.estado == "public":
        return True
    if doc.categoria and puede_acceder_categoria(doc.categoria, usuario):
        return True
    return _tiene_permiso(doc, usuario, {"lectura", "edicion"})


def puede_editar(doc: Documento, usuario: Usuario) -> bool:
    """Return True if the user can edit the document."""
    if usuario.tipo == "admin":
        return True
    if doc.autor_id == usuario.id:
        return True
    if usuario.tipo == "consulta":
        return False
    return _tiene_permiso(doc, usuario, {"edicion"})


def _tiene_permiso(doc: Documento, usuario: Usuario, tipos: set) -> bool:
    """Check explicit ACL entries for a user or any of their groups."""
    grupo_ids = {g.id for g in usuario.grupos}

    for permiso in doc.permisos:
        if permiso.tipo_permiso not in tipos:
            continue
        if permiso.usuario_id == usuario.id:
            return True
        if permiso.grupo_id and permiso.grupo_id in grupo_ids:
            return True
    return False
