"""Which compute unit does Core ML pick for a 4,096 x 4,096 matrix-vector product written as a 1x1 convolution? (REPORT 20.1)
Prints MLComputePlan's preferred device per operation for three compute-unit settings, then times the model on each unit.
Run: uv run --python 3.12 --with coremltools --with numpy python data/ane_plan.py"""
import os, time, numpy as np, coremltools as ct
from coremltools.converters.mil import Builder as mb
from coremltools.converters.mil.mil import types
from coremltools.models.compute_plan import MLComputePlan
HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "ane_conv1.mlpackage")
K = 4096
rng = np.random.default_rng(0)

def build_conv(layers):
    @mb.program(input_specs=[mb.TensorSpec(shape=(1, K, 1, 1), dtype=types.fp16)], opset_version=ct.target.iOS18)
    def prog(x):
        for i in range(layers):
            w = (rng.standard_normal((K, K, 1, 1)) * 0.02).astype(np.float16)
            x = mb.conv(x=x, weight=w, name=f"conv{i}")
        return x
    return ct.convert(prog, convert_to="mlprogram", compute_precision=ct.precision.FLOAT16, minimum_deployment_target=ct.target.iOS18)

def plan_report(path, units):
    cpath = ct.utils.compile_model(path)
    plan = MLComputePlan.load_from_path(cpath, compute_units=units)
    prog = plan.model_structure.program
    out = []
    for fn in prog.functions.values():
        for op in fn.block.operations:
            if op.operator_name in ("const", "constexpr_lut_to_dense", "constexpr_affine_dequantize"): continue
            u = plan.get_compute_device_usage_for_mlprogram_operation(op)
            if u is None: continue
            out.append((op.operator_name, type(u.preferred_compute_device).__name__, [type(d).__name__ for d in u.supported_compute_devices]))
    return out

m = build_conv(1); m.save(PKG)
for name, units in (("CPU_AND_NE", ct.ComputeUnit.CPU_AND_NE), ("CPU_AND_GPU", ct.ComputeUnit.CPU_AND_GPU), ("ALL", ct.ComputeUnit.ALL)):
    print(name, plan_report(PKG, units))
x = {"x": np.zeros((1, K, 1, 1), dtype=np.float16)}
for name, units in (("ANE", ct.ComputeUnit.CPU_AND_NE), ("GPU", ct.ComputeUnit.CPU_AND_GPU), ("CPU", ct.ComputeUnit.CPU_ONLY)):
    t = time.time(); mm = ct.models.MLModel(PKG, compute_units=units); lt = time.time() - t
    for _ in range(20): mm.predict(x)
    ts = []
    for _ in range(150):
        a = time.perf_counter(); mm.predict(x); ts.append(time.perf_counter() - a)
    ts.sort(); print(f"conv1x1 {name}: load {lt:.2f}s, median {ts[75]*1000:.3f} ms, min {ts[0]*1000:.3f} ms")
