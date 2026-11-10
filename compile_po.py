"""Compilador mínimo .po -> .mo en Python puro (sin gettext del sistema).

Uso: python compile_po.py <archivo.po> <archivo.mo>
Soporta msgid/msgstr multilinea y comentarios. Ignora entradas fuzzy.
"""
import array
import struct
import sys


def _parse_po(ruta):
    mensajes = {}
    msgid = None
    msgstr = None
    estado = None  # 'id' o 'str'
    fuzzy = False
    cur_fuzzy = False

    def _flush():
        nonlocal msgid, msgstr, cur_fuzzy
        # Incluye el encabezado (msgid vacío) y omite entradas sin traducción,
        # igual que msgfmt: así gettext cae al msgid original.
        if msgid is not None and msgstr is not None and not cur_fuzzy:
            if msgid == '' or msgstr != '':
                mensajes[msgid] = msgstr
        msgid = msgstr = None
        cur_fuzzy = False

    with open(ruta, encoding='utf-8') as fh:
        for linea in fh:
            linea = linea.rstrip('\n')
            if linea.startswith('#'):
                if 'fuzzy' in linea:
                    cur_fuzzy = True
                continue
            if linea.startswith('msgid '):
                if estado == 'str':
                    _flush()
                msgid = _descomilla(linea[len('msgid '):])
                estado = 'id'
            elif linea.startswith('msgstr '):
                msgstr = _descomilla(linea[len('msgstr '):])
                estado = 'str'
            elif linea.startswith('"'):
                if estado == 'id':
                    msgid += _descomilla(linea)
                elif estado == 'str':
                    msgstr += _descomilla(linea)
            elif linea.strip() == '':
                if estado == 'str':
                    _flush()
                    estado = None
        if estado == 'str':
            _flush()
    return mensajes


def _descomilla(texto):
    texto = texto.strip()
    if texto.startswith('"') and texto.endswith('"'):
        texto = texto[1:-1]
    return texto.encode('utf-8').decode('unicode_escape').encode('latin-1').decode('utf-8')


def _compilar(mensajes, salida):
    claves = sorted(mensajes.keys())
    offsets = []
    ids = b''
    strs = b''
    for clave in claves:
        valor = mensajes[clave]
        bk = clave.encode('utf-8')
        bv = valor.encode('utf-8')
        offsets.append((len(ids), len(bk), len(strs), len(bv)))
        ids += bk + b'\x00'
        strs += bv + b'\x00'

    cantidad = len(claves)
    keystart = 7 * 4 + 16 * cantidad
    valuestart = keystart + len(ids)
    koffsets = []
    voffsets = []
    for o1, l1, o2, l2 in offsets:
        koffsets += [l1, o1 + keystart]
        voffsets += [l2, o2 + valuestart]

    salida_bytes = struct.pack(
        'Iiiiiii',
        0x950412de, 0, cantidad,
        7 * 4, 7 * 4 + cantidad * 8, 0, 0,
    )
    salida_bytes += array.array('i', koffsets).tobytes()
    salida_bytes += array.array('i', voffsets).tobytes()
    salida_bytes += ids
    salida_bytes += strs

    with open(salida, 'wb') as fh:
        fh.write(salida_bytes)


if __name__ == '__main__':
    po, mo = sys.argv[1], sys.argv[2]
    msgs = _parse_po(po)
    _compilar(msgs, mo)
    print(f'Compilado {po} -> {mo} ({len(msgs)} mensajes)')
