

import base64
import ctypes
import json
import os
import struct
import threading
from typing import Any, Dict, Optional

try:
    import orjson
except ImportError:
    orjson = None

import wasmtime


WASM_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "wasm",
    "sha3_wasm_bg.7b9ca65ddd.wasm",
)


def _build_engine() -> wasmtime.Engine:
    
    try:
        config = wasmtime.Config()
        try:
            config.cranelift_opt_level = 2
        except Exception:
            pass
        try:
            config.cache = True
        except Exception:
            pass
        return wasmtime.Engine(config)
    except Exception:
        return wasmtime.Engine()


class _WasmSolver:
    

    __slots__ = (
        "store",
        "instance",
        "memory",
        "alloc",
        "add_stack",
        "wasm_solve",
    )

    def __init__(self, engine: wasmtime.Engine, module: wasmtime.Module):
        self.store = wasmtime.Store(engine)

        linker = wasmtime.Linker(engine)
        try:
            linker.define_wasi()
        except Exception:
            pass

        self.instance = linker.instantiate(self.store, module)
        exports = self.instance.exports(self.store)

        
        self.memory = exports["memory"]
        self.alloc = exports["__wbindgen_export_0"]
        self.add_stack = exports["__wbindgen_add_to_stack_pointer"]
        self.wasm_solve = exports["wasm_solve"]

    def _write(self, ptr: int, data: bytes):
        
        view = self.memory.data_ptr(self.store)

        if isinstance(view, int):
            src = ctypes.create_string_buffer(data, len(data))
            ctypes.memmove(view + ptr, src, len(data))
            return view

        try:
            view[ptr : ptr + len(data)] = data
        except Exception:
            for i, b in enumerate(data):
                view[ptr + i] = b

        return view

    def calculate_hash(
        self,
        algorithm: str,
        challenge: str,
        salt: str,
        difficulty: int,
        expire_at: int,
    ) -> Optional[int]:
        
        challenge_b = challenge.encode("utf-8")
        prefix_b = f"{salt}_{expire_at}_".encode("utf-8")

        store = self.store

        
        retptr = self.add_stack(store, -16)

        try:
            
            
            c_ptr = self.alloc(store, len(challenge_b), 1)
            if c_ptr is None:
                raise RuntimeError("WASM allocator returned null pointer for challenge")
            self._write(c_ptr, challenge_b)

            p_ptr = self.alloc(store, len(prefix_b), 1)
            if p_ptr is None:
                raise RuntimeError("WASM allocator returned null pointer for prefix")
            self._write(p_ptr, prefix_b)

            self.wasm_solve(
                store,
                retptr,
                c_ptr,
                len(challenge_b),
                p_ptr,
                len(prefix_b),
                float(difficulty),
            )

            
            view = self.memory.data_ptr(store)
            try:
                status = struct.unpack_from("<i", view, retptr)[0]
                if status == 0:
                    return None

                value = struct.unpack_from("<d", view, retptr + 8)[0]
            except Exception:
                
                if isinstance(view, int):
                    raw = ctypes.string_at(view + retptr, 16)
                else:
                    raw = bytes(view[retptr : retptr + 16])

                status = int.from_bytes(raw[:4], "little", signed=True)
                if status == 0:
                    return None

                value = struct.unpack("<d", raw[8:16])[0]

            return int(value)

        finally:
            
            self.add_stack(store, 16)


class DeepSeekHash:
    

    __slots__ = ("engine", "module", "_local")

    def __init__(self):
        self.engine = _build_engine()

        with open(WASM_PATH, "rb") as f:
            wasm_bytes = f.read()

        self.module = wasmtime.Module(self.engine, wasm_bytes)
        self._local = threading.local()

    def _solver(self) -> _WasmSolver:
        solver = getattr(self._local, "solver", None)

        if solver is None:
            solver = _WasmSolver(self.engine, self.module)
            self._local.solver = solver

        return solver

    def calculate_hash(
        self,
        algorithm: str,
        challenge: str,
        salt: str,
        difficulty: int,
        expire_at: int,
    ) -> Optional[int]:
        return self._solver().calculate_hash(
            algorithm,
            challenge,
            salt,
            difficulty,
            expire_at,
        )


class DeepSeekPOW:
    __slots__ = ("hasher",)

    def __init__(self):
        self.hasher = DeepSeekHash()

    def solve_challenge(self, config: Dict[str, Any]) -> str:
        
        answer = self.hasher.calculate_hash(
            config["algorithm"],
            config["challenge"],
            config["salt"],
            config["difficulty"],
            config["expire_at"],
        )

        if answer is None:
            raise RuntimeError("Failed to solve DeepSeek PoW challenge")

        result = {
            "algorithm": config["algorithm"],
            "challenge": config["challenge"],
            "salt": config["salt"],
            "answer": answer,
            "signature": config["signature"],
            "target_path": config["target_path"],
        }

        if orjson is not None:
            raw = orjson.dumps(
                result,
                option=getattr(orjson, "OPT_COMPACT", 0),
            )
        else:
            raw = json.dumps(
                result,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")

        return base64.b64encode(raw).decode("ascii")