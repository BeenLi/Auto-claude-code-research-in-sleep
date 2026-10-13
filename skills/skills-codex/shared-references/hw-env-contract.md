# Hardware Environment Contract (local extension)

> Extends [`compute-env-contract.md`](compute-env-contract.md) for this fork's
> simulator, RTL, FPGA, and GPU-workload experiments. That upstream file is kept
> verbatim so future syncs merge without conflicts; everything hardware-specific
> lives here. Read the upstream file first for the spec / ledger /
> three-tier-validation idea; this file only states the deltas.

## 0. Two files, two lifetimes

| File | What it records | Lifetime | Where |
|---|---|---|---|
| Lab inventory | Which hardware and tools the lab has | Stable, shared by every project | [`lab-resources.yaml`](lab-resources.yaml) in this directory. A project may override it with `<project>/.aris/compute/lab-resources.yaml`. |
| Env-spec | How one software stack is built and validated | Per project, hashed | `<project>/.aris/compute/env-spec.yaml`, started from `templates/HW_ENV_SPEC_TEMPLATE.yaml` |

Resolve the inventory in this order and say which one was used:

```bash
INV=""
for c in .aris/compute/lab-resources.yaml \
         .claude/skills/shared-references/lab-resources.yaml \
         .agents/skills/shared-references/lab-resources.yaml \
         .gemini/skills/shared-references/lab-resources.yaml \
         skills/shared-references/lab-resources.yaml \
         "${ARIS_REPO:-/nonexistent}/skills/shared-references/lab-resources.yaml"; do
  [ -f "$c" ] && { INV="$c"; break; }
done
[ -n "$INV" ] && echo "lab inventory: $INV" || echo "WARN: lab-resources.yaml not found; feasibility falls back to the generic rubric" >&2
```

The first path is the project override. The next three are where
`tools/install_aris.sh` links `shared-references/` for Claude, Codex, and
Gemini installs. The last two cover running inside the ARIS repo itself.

A `null` field means "not yet recorded", not "absent". Do not score an idea as
blocked because a field is null; score it on what is known and list the null
fields the idea depends on in its `main_blocker` notes.

**Tracking.** Upstream treats `.aris/` as uncommitted. In this fork, keep
`.aris/compute/` tracked in the project's git: the env-spec and ledger are the
provenance an artifact-evaluation committee asks for.

## 1. Facts that change feasibility scores

- **Resource-overhead numbers do not need a board.** LUT / FF / BRAM / DSP
  utilization, timing slack, and achieved Fmax come from Vivado synthesis and
  implementation, which run on the CPU server. They consume RAM and a Vivado
  license (`license_vivado` slot). Only on-board measurement or emulation needs
  an `fpga_vcu118` slot.
- **gem5 is single-threaded per simulation.** Parallel sweep width is bounded
  by `memory_gib / peak RSS per instance`, then by `cores - reserved_cores`.
  Full-system runs: boot once, checkpoint, restore many.
- **Verilator scales with `--threads`.** Build once per configuration, run many.
- **The L40s are PCIe-only.** They cannot faithfully reproduce a baseline whose
  claim depends on NVLink / NVSwitch bandwidth. Their strong role here is
  running real LLM workloads at small scale to produce traces and profiles that
  feed gem5 / htsim, and serving models that fit in 48 GB per GPU without
  tensor parallelism across PCIe.
- **Three boards means at most three concurrent on-board jobs.** Bitstream
  builds are separate jobs on `license_vivado`; the board slot is held only for
  programming and measurement.
- **One server, no Ethernet switch, one-to-one links only.** Direct cables
  exist, so a real-hardware network experiment can run between two endpoints on
  one point-to-point link (BF2 to VCU118, or VCU118 to VCU118), with as many
  flows or QPs on that link as the stacks allow. Anything that needs more than
  two endpoints, a switch queue, incast from several senders, or multi-node
  collectives runs in htsim. Whether that is good enough depends on the claim
  (§2).
- **Two kinds of RDMA endpoint.** The BF2 is a working RDMA NIC with Arm cores
  for offload. A VCU118 becomes an RDMA NIC only with a RoCE stack on the FPGA;
  until `fpga.rdma_stack` records one that runs, the NIC itself is something to
  build, not something to configure.
- **FPGA simulation acceleration needs a shell.** Before scoring an
  FPGA-accelerated simulation idea as near-ready, confirm the flow (for example
  FireSim, or an in-house emulation shell) lists a VCU118 platform. Otherwise
  the shell itself is the adapter: `evaluation_adapter_cost: new_platform`.

## 2. Resource fit → `platform_workload_access` (lab policy)

`/idea-creator` uses this table to set `platform_workload_access` for every
idea, before any reviewer sees it. If the inventory cannot be resolved, it falls
back to the generic `evaluation_feasibility_score` descriptions in its rubric.

Score the route the decisive claim needs, not the most impressive route. A claim
the target venue accepts from simulation is scored on the simulator. A claim
that only real hardware can support is scored on the hardware.

| `platform_workload_access` | Fits when | Example |
|---|---|---|
| `ready` | Every resource the decisive experiment needs is in the inventory and validated: a simulator or Vivado env with a passing ledger entry, at most one VCU118 with an existing build flow, the BF2 as installed, L40s without an NVLink assumption, and the workload or trace in hand. | gem5 / htsim sweep of compression ratio against Rx pressure; LUT / BRAM / Fmax of a compression engine on the XCVU9P; KV-cache trace capture on one L40 |
| `near_ready` | The hardware is in the lab and only software bring-up of a few days stands in the way: a pinned toolchain not yet built, a new simulator component, a first verbs or DOCA program on the BF2, or a one-to-one link test over the existing direct cables. | DOCA offload micro-benchmark on the BF2 Arm cores; BF2 to VCU118 point-to-point throughput test |
| `nontrivial` | The hardware is in the lab but a major function must be built or ported first: the FPGA as an RDMA NIC while `fpga.rdma_stack` is null, an emulation shell on the VCU118, a design split across two or three boards, or a scale-out claim built from one calibrated real link plus htsim. | Port a RoCEv2 stack to the VCU118 and add inline compression; calibrate one BF2 link, then scale to many nodes in htsim |
| `weak` | The decisive claim is about hardware the lab lacks, and a simulator or model can carry it only with fidelity caveats a reviewer will likely press: more than two real endpoints or any switch behavior, more than three FPGAs, more than eight GPUs, or NVLink-class bandwidth. | End-to-end multi-node all-reduce time with in-NIC compression, where reviewers expect a real cluster but only htsim is available |
| `blocked` | The decisive claim can only be supported by hardware, silicon, or data the lab cannot get. | ASIC area or power from silicon; production-cluster traffic traces; an offload engine that exists only in closed silicon the lab does not have and cannot emulate on the FPGA |

**Writing `revisit_condition` for resource gaps.** When an idea lands below
`near_ready` because of the lab, name the missing item in inventory terms, so a
later inventory change can find it with a text search. Examples:
`needs: ethernet_switch=true and a second server`; `needs: fpga.rdma_stack recorded`;
`needs: more than two endpoints (have one-to-one links only)`; `needs: 4 VCU118 boards (have 3)`;
`needs: NVLink-class GPU interconnect`; `needs: toolchains.vcs.available=true`.

## 3. Job shapes and queue slot types

| Job | Slot type | Cores | Memory | Notes |
|---|---|---|---|---|
| gem5 SE / micro-benchmark | `cpu_sim` | 1 | measured peak RSS | Sweep width per §1 |
| gem5 full-system | `cpu_sim` | 1 | simulated memory size plus overhead | Restore from checkpoints |
| htsim network simulation | `cpu_sim` | 1 | measured | |
| Verilator RTL simulation | `cpu_rtl` | value of `--threads` | measured | |
| Vivado synthesis / implementation | `license_vivado` | up to 8 | budget generously until the ledger has a measured peak | Vivado caps `general.maxThreads` at 8 |
| On-board measurement / emulation | `fpga_vcu118` | 1 | small | Needs a bitstream from an earlier build job |
| BF2 micro-benchmark / offload | `dpu_bf2` | 2 | small | Link tests need a peer on a direct cable |
| LLM workload, trace capture, profiling | `gpu_l40` | 8 | measured | One L40 per job unless the model needs more than 48 GB |

Derive the queue's slots from the inventory. Example for the current lab:

```yaml
resources:
  slots:
    - {id: sim00, type: cpu_sim}        # repeat to the sweep width from §1
    - {id: rtl0,  type: cpu_rtl}
    - {id: viv0,  type: license_vivado} # repeat to limits.vivado_parallel_jobs
    - {id: l40_0, type: gpu_l40, gpu: 0}  # gpu: sets CUDA_VISIBLE_DEVICES
    - {id: fpga0, type: fpga_vcu118}
    - {id: fpga1, type: fpga_vcu118}
    - {id: fpga2, type: fpga_vcu118}
    - {id: bf2,   type: dpu_bf2}
```

The queue exports `ARIS_RESOURCE_SLOT` and substitutes `${RESOURCE_SLOT}` in the
job command. For board jobs, map the slot id to `hw_server_target` through the
inventory. The queue keeps slots exclusive only within one run, so jobs on an
exclusive device (`fpga_vcu118`, `dpu_bf2`) also take a per-device lock that
holds across runs and manual sessions:

```bash
exec 9>"/tmp/aris-dev-${ARIS_RESOURCE_SLOT}.lock"
flock -n 9 || { echo "device ${ARIS_RESOURCE_SLOT} busy" >&2; exit 75; }
# program the bitstream or run the BF2 program, then measure here
```

A one-to-one link test holds both ends' locks.

## 4. Hardware env-spec: deltas from upstream §2

| Upstream field | Hardware form |
|---|---|
| `base` | OS plus build prerequisites (Python, SCons, autoconf). |
| `pip_phases` | `build_phases`: ordered shell commands. Order matters for the same reason: a later step must not silently rebuild against a different toolchain. GPU envs keep upstream `pip_phases`. |
| (none) | `source.rev`: the simulator tag or commit. A null rev blocks validation. |
| (none) | `source.version` for vendor tools: the Vivado version, which also fixes IP-core versions. |
| `env` | Tool paths and license variables such as `XILINXD_LICENSE_FILE`. |
| tier fields | `resource_shape`: slot type, cores, memory. Must match §3. |
| `smoke.gpu_tests` | `smoke.witness`: a tiny run with an `expect` regex (gem5 hello exit tick, Verilator display, Vivado synthesis on the VU9P part, `hw_server` target list, `nvidia-smi` device list). |

Hash each environment separately, so editing one never invalidates another:

```bash
python3 -c 'import sys,json,hashlib,yaml
for k,v in yaml.safe_load(open(sys.argv[1])).items():
    print(k, hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()[:8])' .aris/compute/env-spec.yaml
```

The spec hash catches spec edits. It cannot see someone upgrading Vivado on the
server, so every ledger block also records the versions the witness observed;
a mismatch on the next run is drift even when the hash is unchanged.

Ledger block, appended to `.aris/compute/<host-id>.md`:

```
### env: vivado-vu9p@0c9639de
host: sim-server
observed: vivado v<version>; license <type>
shape: {slot: license_vivado, cpus: 8, peak_rss_gib: <measured>}
validated: <UTC date> (cli + witness; agent-follows-doc <date or pending>)
gotcha: <any §5 row hit on this host>
```

## 5. Validation and diagnosis

Tiers are upstream §4 with hardware probes: tier 1 runs `smoke.cli_checks`,
tier 2 runs `smoke.witness`, tier 3 (agent-follows-doc) is unchanged. Run tiers
1 and 2 before the first job of every session and after any rebuild.

| Symptom | Layer | Fix |
|---|---|---|
| SCons or Python errors while building gem5 | spec | Pin Python and SCons in `base`; match the gem5 release notes |
| gem5 jobs killed in a wide sweep | exec | Lower the `cpu_sim` slot count to memory / peak RSS |
| gem5 hangs fetching a resource | weights | The server has no internet; pre-stage gem5-resources on persistent scratch |
| Same RTL gives different results after an update | spec | Verilator version drifted; pin `source.rev` and compare observed versions |
| `License checkout failed` or part not licensed | env | Check the license variable and that the job runs on the licensed host |
| Vivado implementation killed | exec | Lower `limits.vivado_parallel_jobs`; record the measured peak |
| Achieved clock below the target | result | Report WNS and achieved Fmax; never claim the target clock |
| `get_hw_targets` shows fewer boards than the inventory | device | Another session holds the cable, a board is off, or `host` is wrong |
| Multi-GPU run much slower than expected | platform | PCIe-only interconnect; this is the platform, not a bug |
| BF2 port stays `PORT_DOWN` | device | Links are direct cables only; check the pair in `direct_links.pairs` and that the peer endpoint is up |
| Host sees a different BF2 data path than expected | env | Record the BF2 mode (DPU, separated host, NIC) in the ledger; it changes what the host sees |

## 6. How skills use this

- `/idea-creator`: Phase 2 sees a one-paragraph inventory summary. Phase 3 sets
  `platform_workload_access` with §2 and writes resource gaps as
  `revisit_condition`.
- `/experiment-plan`: the Validation Budget states slot types and slot-hours.
- `/experiment-bridge`: before sanity runs, resolve the inventory and the
  env-spec, run tiers 1 and 2, and append the ledger block.
- `/run-experiment`: read the ledger before launch and take the device lock
  for FPGA and BF2 jobs.
- `/experiment-queue`: build `resources.slots` from §3.
- `/research-refine`: the default FPGA synthesis target is the inventory's part.
