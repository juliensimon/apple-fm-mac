#!/usr/bin/env python3
"""How fast can the Neural Engine stream weights? Time 1x1-convolution matrix-vector products of growing weight size.

A matrix-vector product reads every weight once and does almost no arithmetic per byte, so its time is set by how
fast the compute unit pulls weights from memory. The slope of time against weight bytes is 1 / bandwidth; the
intercept is the fixed cost of one Core ML prediction. Compared across compute units (ANE, GPU, CPU) and weight formats
(16-bit, 8-bit, palettized 4-bit and 2-bit). Public Core ML API only. Every ANE model is checked with MLComputePlan so a
silent fallback to the GPU or CPU is flagged.

Run: uv run --python 3.12 --with coremltools --with numpy python data/ane_bw.py [formats]
Writes data/ane_bw.json and one .mlpackage per model in data/. The published results are two runs of this script:
`fp16` (saved as ane_bw_fp16.json) and `int8,lut4,lut2` (saved as ane_bw_formats.json).
"""
import json, os, statistics as st, sys, time
import numpy as np
import coremltools as ct
import coremltools.optimize.coreml as cto
from coremltools.converters.mil import Builder as mb
from coremltools.converters.mil.mil import types
from coremltools.models.compute_plan import MLComputePlan

HERE = os.path.dirname(os.path.abspath(__file__))
K = 4096
rng = np.random.default_rng(0)


def build(layers):
    @mb.program(input_specs=[mb.TensorSpec(shape=(1, K, 1, 1), dtype=types.fp16)], opset_version=ct.target.iOS18)
    def prog(x):
        for i in range(layers):
            w = (rng.standard_normal((K, K, 1, 1)) * 0.02).astype(np.float16)
            x = mb.conv(x=x, weight=w, name=f"conv{i}")
        return x
    return ct.convert(prog, convert_to="mlprogram", compute_precision=ct.precision.FLOAT16, minimum_deployment_target=ct.target.iOS18)


def preferred_devices(path, units):
    cpath = ct.utils.compile_model(path)
    plan = MLComputePlan.load_from_path(cpath, compute_units=units)
    devs = []
    for fn in plan.model_structure.program.functions.values():
        for op in fn.block.operations:
            if op.operator_name in ("const",) or op.operator_name.startswith("constexpr"): continue
            u = plan.get_compute_device_usage_for_mlprogram_operation(op)
            if u is not None: devs.append(type(u.preferred_compute_device).__name__.replace("ML", "").replace("ComputeDevice", ""))
    return devs


def timeit(model, n=200, warm=30):
    x = {"x": np.zeros((1, K, 1, 1), dtype=np.float16)}
    for _ in range(warm): model.predict(x)
    ts = []
    for _ in range(n):
        t = time.perf_counter(); model.predict(x); ts.append(time.perf_counter() - t)
    ts.sort()
    return st.median(ts) * 1000, ts[0] * 1000, ts[int(n * 0.9)] * 1000


def compress(m, fmt):
    if fmt == "int8":
        return cto.linear_quantize_weights(m, cto.OptimizationConfig(global_config=cto.OpLinearQuantizerConfig(mode="linear_symmetric", dtype="int8", granularity="per_channel")))
    if fmt in ("lut4", "lut2"):
        nbits = 4 if fmt == "lut4" else 2
        return cto.palettize_weights(m, cto.OptimizationConfig(global_config=cto.OpPalettizerConfig(mode="uniform", nbits=nbits, granularity="per_tensor")))
    return m


results = []
formats = sys.argv[1].split(",") if len(sys.argv) > 1 else ["fp16", "int8", "lut4", "lut2"]
for fmt in formats:
    for layers in (1, 2, 4, 8):
        t0 = time.time()
        try:
            m = compress(build(layers), fmt)
            path = os.path.join(HERE, f"ane_bw_{fmt}_{layers}.mlpackage"); m.save(path)
        except Exception as e:
            print("build fail", fmt, layers, str(e)[:160], flush=True); continue
        size_mib = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(path) for f in fs) / 2**20
        fp16_mib = layers * K * K * 2 / 2**20
        for name, units in (("ANE", ct.ComputeUnit.CPU_AND_NE), ("GPU", ct.ComputeUnit.CPU_AND_GPU), ("CPU", ct.ComputeUnit.CPU_ONLY)):
            if fmt != "fp16" and name != "ANE": continue
            try:
                pref = preferred_devices(path, units) if name != "CPU" else ["CPU"] * layers
                mm = ct.models.MLModel(path, compute_units=units)
                med, mn, p90 = timeit(mm)
                row = {"format": fmt, "layers": layers, "package_mib": round(size_mib, 1), "fp16_equiv_mib": fp16_mib, "units": name, "median_ms": round(med, 4), "min_ms": round(mn, 4), "p90_ms": round(p90, 4),
                       "devices_preferred": sorted(set(pref)), "all_on_requested_unit": all((name[:3].lower() in d.lower()) or (name == "ANE" and "Neural" in d) for d in pref)}
            except Exception as e:
                row = {"format": fmt, "layers": layers, "package_mib": round(size_mib, 1), "units": name, "error": str(e)[:160]}
            results.append(row)
            print(json.dumps(row), flush=True)
        json.dump(results, open(os.path.join(HERE, "ane_bw.json"), "w"), indent=1)
        print(f"   [{fmt} x{layers} took {time.time() - t0:.0f}s]", flush=True)
print("done")
