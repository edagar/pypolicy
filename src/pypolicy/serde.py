from __future__ import annotations
import json, zlib
from typing import Iterable, List, Tuple
from .vm import (
    Opcode, Instruction,
    iObject, iNil, iInteger, iBool, iString, iFunction,
)

MAGIC = b"PPBC"
VERSION = 1

OPCODE_TO_BYTE = {
    Opcode.BIN_ADD:      0x01,
    Opcode.BIN_SUB:      0x02,
    Opcode.BIN_MUL:      0x03,
    Opcode.BIN_DIV:      0x04,
    Opcode.BIN_MOD:      0x05,
    Opcode.BIN_IN:       0x06,
    Opcode.EQ:           0x10,
    Opcode.NEQ:          0x11,
    Opcode.GT:           0x12,
    Opcode.LT:           0x13,
    Opcode.GTE:          0x14,
    Opcode.LTE:          0x15,
    Opcode.NOT:          0x16,

    Opcode.PUSH:         0x20,
    Opcode.POP:          0x21,
    Opcode.STORE:        0x22,
    Opcode.PUSH_GLOBAL:  0x23,
    Opcode.PUSH_LOCAL:   0x24,
    Opcode.STORE_LOCAL:  0x25,

    Opcode.CALL_FN:      0x30,
    Opcode.RETURN:       0x31,

    Opcode.GETATTR:      0x40,
    Opcode.GETITEM:      0x41,  # legacy compatibility
    Opcode.INDEX:        0x42,
    Opcode.SET_INDEX:    0x43,
    Opcode.SET_ATTR:     0x44,

    Opcode.MAKE_LIST:    0x50,
    Opcode.MAKE_DICT:    0x51,

    Opcode.ITER_INIT:    0x60,
    Opcode.ITER_NEXT:    0x61,

    Opcode.JUMP:         0x70,
    Opcode.JUMP_IF_TRUE: 0x71,
    Opcode.JUMP_IF_FALSE:0x72,

    Opcode.PRINT:        0x80,
}
BYTE_TO_OPCODE = {v: k for k, v in OPCODE_TO_BYTE.items()}


def _uvar(n: int) -> bytes:
    if n < 0:
        raise ValueError("uvar expects non-negative")
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _read_uvar(buf: memoryview, i: int) -> tuple[int, int]:
    shift = 0
    out = 0
    while True:
        b = buf[i]; i += 1
        out |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            return out, i
        shift += 7


def _zigzag(n: int) -> int:
    return (n << 1) if n >= 0 else ((-n << 1) - 1)


def _unzag(n: int) -> int:
    return (n >> 1) if (n & 1) == 0 else (-( (n >> 1) + 1 ))


TAG_NIL  = 0
TAG_INT  = 1
TAG_BOOL = 2
TAG_STR  = 3
TAG_FUNC = 4

def _enc_str(s: str) -> bytes:
    b = s.encode("utf-8")
    return _uvar(len(b)) + b


def _dec_str(buf: memoryview, i: int) -> tuple[str, int]:
    ln, i = _read_uvar(buf, i)
    if i + ln > len(buf): raise ValueError("string length out of range")
    s = bytes(buf[i:i+ln]).decode("utf-8")
    return s, i + ln


def _enc_int(n: int) -> bytes:
    return _uvar(_zigzag(n))


def _dec_int(buf: memoryview, i: int) -> tuple[int, int]:
    v, i = _read_uvar(buf, i)
    return _unzag(v), i


def _enc_arg(arg: iObject | None) -> bytes:
    if arg is None or isinstance(arg, iNil):
        return bytes([TAG_NIL])

    match arg:
        case iInteger():
            return bytes([TAG_INT]) + _enc_int(int(arg.value()))

        case iBool():
            return bytes([TAG_BOOL, 1 if arg.value() else 0])

        case iString():
            return bytes([TAG_STR]) + _enc_str(arg.value())

        case iFunction():
            payload = bytearray()
            n_params = int(arg.n_params.value())
            payload += _uvar(n_params)
            for name in arg.param_names:
                payload += _enc_str(name)
            nested = _enc_stream(arg.code)  # no header; just the instruction stream
            payload += _uvar(len(nested)) + nested
            return bytes([TAG_FUNC]) + bytes(payload)

    raise TypeError(f"Cannot serialize arg type: {type(arg).__name__}")


def _dec_arg(buf: memoryview, i: int) -> tuple[iObject, int]:
    tag = buf[i]; i += 1
    if tag == TAG_NIL:
        return iNil(), i
    if tag == TAG_INT:
        from .vm import iInteger as _iInteger
        val, i = _dec_int(buf, i)
        return _iInteger(val), i
    if tag == TAG_BOOL:
        from .vm import iBool as _iBool
        b = bool(buf[i]); i += 1
        return _iBool(b), i
    if tag == TAG_STR:
        from .vm import iString as _iString
        s, i = _dec_str(buf, i)
        return _iString(s), i
    if tag == TAG_FUNC:
        from .vm import iFunction as _iFunction, iInteger as _iInteger
        n_params, i = _read_uvar(buf, i)
        param_names: List[str] = []
        for _ in range(n_params):
            s, i = _dec_str(buf, i)
            param_names.append(s)
        blob_len, i = _read_uvar(buf, i)
        if blob_len < 0 or i + blob_len > len(buf):
            raise ValueError("function blob length out of range")
        sub = buf[i:i+blob_len]; i += blob_len
        nested_code, _ = _dec_stream(sub, 0)
        fn = _iFunction(nested_code, _iInteger(n_params), param_names)
        return fn, i
    raise ValueError(f"Unknown arg tag {tag}")


def _enc_stream(code: Iterable[Instruction]) -> bytes:
    out = bytearray()
    for op, arg in code:
        try:
            out.append(OPCODE_TO_BYTE[op])
        except KeyError:
            raise ValueError(f"Unknown opcode {op}")
        out += _enc_arg(arg)
    return bytes(out)


def _dec_stream(buf: memoryview, i0: int) -> tuple[List[Instruction], int]:
    i = i0
    code: List[Instruction] = []
    n = len(buf)
    while i < n:
        opb = buf[i]; i += 1
        if opb not in BYTE_TO_OPCODE:
            raise ValueError(f"Unknown opcode byte 0x{opb:02x}")
        op = BYTE_TO_OPCODE[opb]
        arg, i = _dec_arg(buf, i)  # always one arg tag (may be NIL)
        code.append((op, arg))
    return code, i

def _pack(body: bytes, meta: dict | None, flags: int = 0) -> bytes:
    meta_bytes = json.dumps(meta or {}, separators=(",", ":")).encode("utf-8")
    compressed_body = zlib.compress(body)
    header = bytearray()
    header += MAGIC
    header += VERSION.to_bytes(2, "big")                # VERSION=1
    header += int(flags).to_bytes(2, "big")             # FLAGS
    header += len(meta_bytes).to_bytes(4, "big")        # META_LEN
    header += len(compressed_body).to_bytes(4, "big")   # BODY_LEN
    crc = zlib.crc32(compressed_body) & 0xFFFFFFFF
    header += crc.to_bytes(4, "big")                    # CRC32 (body only)
    return bytes(header) + meta_bytes + compressed_body


def _unpack(mv: memoryview) -> tuple[bytes, dict]:
    if len(mv) < 6 or bytes(mv[:4]) != MAGIC:
        raise ValueError("bad magic")
    ver = int.from_bytes(bytes(mv[4:6]), "big")
    if ver != VERSION:
        raise ValueError(f"unsupported bytecode version {ver}")
    i = 6
    flags = int.from_bytes(bytes(mv[i:i+2]), "big"); i += 2
    meta_len = int.from_bytes(bytes(mv[i:i+4]), "big"); i += 4
    body_len = int.from_bytes(bytes(mv[i:i+4]), "big"); i += 4
    crc_expect = int.from_bytes(bytes(mv[i:i+4]), "big"); i += 4

    end_meta = i + meta_len
    end_body = end_meta + body_len
    if end_meta > len(mv) or end_body > len(mv):
        raise ValueError("bytecode header lengths out of range")

    meta_json = bytes(mv[i:end_meta])
    try:
        meta = json.loads(meta_json.decode("utf-8")) if meta_len else {}
    except Exception as e:
        raise ValueError(f"invalid metadata json: {e}") from e

    body = bytes(mv[end_meta:end_body])
    if (zlib.crc32(body) & 0xFFFFFFFF) != crc_expect:
        raise ValueError("bytecode CRC mismatch")

    return zlib.decompress(body), meta


# ---- public API ----
def serialize(code: Iterable[Instruction], *, meta: dict | None = None) -> bytes:
    body = _enc_stream(code)
    return _pack(body, meta=meta, flags=0)


def deserialize(blob: bytes) -> List[Instruction]:
    body, _ = _unpack(memoryview(blob))
    code, _ = _dec_stream(memoryview(body), 0)
    return code


def peek_metadata(blob: bytes) -> dict:
    """Return metadata dict without decoding the instruction stream."""
    _, meta = _unpack(memoryview(blob))
    return meta

