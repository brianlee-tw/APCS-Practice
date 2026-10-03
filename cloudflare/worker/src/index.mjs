var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// src/routing.ts
var LESSON_ROUTES = {
  "fnd/io-types-expressions": {
    unitId: "U-FND",
    lessonId: "L-FND-01",
    unitSlug: "fnd",
    lessonSlug: "io-types-expressions",
    assetPath: "/_internal/l-fnd-01.html",
    defaultPb: "PB-142",
    problems: ["PB-142", "PB-143", "PB-144"],
    labs: [
      "fnd-value-flow",
      "fnd-integer-division",
      "fnd-micro-practice",
      "fnd-code-state-stepper",
      "fnd-expression-trace",
      "fnd-io-contract",
      "fnd-type-fit",
      "fnd-testcase-lab",
      "fnd-bug-hunt",
      "fnd-bitwise-basics",
      "fnd-exit-console"
    ]
  },
  "fnd/control-flow-loops": {
    unitId: "U-FND",
    lessonId: "L-FND-02",
    unitSlug: "fnd",
    lessonSlug: "control-flow-loops",
    assetPath: "/_internal/l-fnd-02.html",
    defaultPb: "PB-96",
    problems: ["PB-96", "PB-40", "PB-20"],
    labs: ["fnd02-control-flow-router", "fnd02-loop-state-stepper", "fnd02-invariant-builder", "fnd02-off-by-one", "fnd02-break-continue", "fnd02-reading-trace", "fnd02-boundary-tests", "fnd02-exit-console"]
  },
  "fnd/functions-scope-reference": {
    unitId: "U-FND",
    lessonId: "L-FND-03",
    unitSlug: "fnd",
    lessonSlug: "functions-scope-reference",
    assetPath: "/_internal/l-fnd-03.html",
    defaultPb: "PB-145",
    problems: ["PB-145", "PB-146", "PB-151", "PB-147"],
    labs: ["fnd03-call-boundary", "fnd03-scope-explorer", "fnd03-value-reference", "fnd03-side-effect-trace", "fnd03-decomposition", "fnd03-reading-call-trace", "fnd03-signature-interface", "fnd03-exit-console"]
  },
  "fnd/numeric-boundary-debug": {
    unitId: "U-FND",
    lessonId: "L-FND-04",
    unitSlug: "fnd",
    lessonSlug: "numeric-boundary-debug",
    assetPath: "/_internal/l-fnd-04.html",
    defaultPb: "PB-148",
    problems: ["PB-148", "PB-41", "PB-150", "PB-149"],
    labs: ["fnd04-first-divergence", "fnd04-integer-conversion", "fnd04-overflow-type-fit", "fnd04-boundary-builder", "fnd04-off-by-one", "fnd04-ub-bug-hunt", "fnd04-minimal-counterexample", "fnd04-exit-console"]
  },
  "dat/array-vector": {
    unitId: "U-DAT",
    lessonId: "L-DAT-01",
    unitSlug: "dat",
    lessonSlug: "array-vector",
    assetPath: "/_internal/l-dat-01.html",
    defaultPb: "PB-152",
    problems: ["PB-152", "PB-98", "PB-153"],
    labs: [
      "dat01-index-boundary",
      "dat01-vector-state",
      "dat01-traversal-trace",
      "dat01-storage-choice",
      "dat01-boundary-bug-hunt",
      "dat01-exit-console"
    ]
  },
  "dat/string-processing": {
    unitId: "U-DAT",
    lessonId: "L-DAT-02",
    unitSlug: "dat",
    lessonSlug: "string-processing",
    assetPath: "/_internal/l-dat-02.html",
    defaultPb: "PB-97",
    problems: ["PB-97", "PB-10", "PB-42"],
    labs: [
      "dat02-char-index",
      "dat02-source-destination",
      "dat02-input-contract",
      "dat02-scan-state",
      "dat02-string-bug-hunt",
      "dat02-exit-console"
    ]
  },
  "dat/matrix-2d": {
    unitId: "U-DAT",
    lessonId: "L-DAT-03",
    unitSlug: "dat",
    lessonSlug: "matrix-2d",
    assetPath: "/_internal/l-dat-03.html",
    defaultPb: "PB-154",
    problems: ["PB-154", "PB-37", "PB-9"],
    labs: [
      "dat03-coordinate-space",
      "dat03-transform-mapping",
      "dat03-neighbor-boundary",
      "dat03-shape-tests",
      "dat03-exit-console"
    ]
  },
  "dat/simulation": {
    unitId: "U-DAT",
    lessonId: "L-DAT-04",
    unitSlug: "dat",
    lessonSlug: "simulation",
    assetPath: "/_internal/l-dat-04.html",
    defaultPb: "PB-155",
    problems: ["PB-155", "PB-114", "PB-120", "PB-115"],
    labs: [
      "dat04-state-table",
      "dat04-transition-order",
      "dat04-termination",
      "dat04-first-divergence",
      "dat04-testcase-builder",
      "dat04-exit-console"
    ]
  },
  "psv/constraints-baseline": {
    unitId: "U-PSV",
    lessonId: "L-PSV-01",
    unitSlug: "psv",
    lessonSlug: "constraints-baseline",
    assetPath: "/_internal/l-psv-01.html",
    defaultPb: "PB-156",
    problems: ["PB-156", "PB-157", "PB-158"],
    labs: [
      "psv01-constraint-budget",
      "psv01-candidate-space",
      "psv01-baseline-oracle",
      "psv01-bottleneck-lens",
      "psv01-exit-console"
    ]
  },
  "psv/complexity": {
    unitId: "U-PSV",
    lessonId: "L-PSV-02",
    unitSlug: "psv",
    lessonSlug: "complexity",
    assetPath: "/_internal/l-psv-02.html",
    defaultPb: "PB-159",
    problems: ["PB-159", "PB-160", "PB-161"],
    labs: [
      "psv02-operation-budget",
      "psv02-loop-shape",
      "psv02-time-space-tradeoff",
      "psv02-amortized-vector",
      "psv02-exit-console"
    ]
  },
  "psv/code-reasoning": {
    unitId: "U-PSV",
    lessonId: "L-PSV-03",
    unitSlug: "psv",
    lessonSlug: "code-reasoning",
    assetPath: "/_internal/l-psv-03.html",
    defaultPb: "PB-162",
    problems: ["PB-162", "PB-163", "PB-164", "PB-165"],
    labs: [
      "psv03-first-divergence",
      "psv03-trace-table",
      "psv03-minimal-counterexample",
      "psv03-completion-invariant",
      "psv03-patch-regression",
      "psv03-exit-console"
    ]
  },
  "psv/math-correctness": {
    unitId: "U-PSV",
    lessonId: "L-PSV-04",
    unitSlug: "psv",
    lessonSlug: "math-correctness",
    assetPath: "/_internal/l-psv-04.html",
    defaultPb: "PB-166",
    problems: ["PB-166", "PB-167", "PB-168", "PB-131"],
    labs: [
      "psv04-correctness-claim-board",
      "psv04-gcd-lcm-state",
      "psv04-mod-divisibility",
      "psv04-counterexample-builder",
      "psv04-exit-console"
    ]
  },
  "ord/sorting": {
    unitId: "U-ORD",
    lessonId: "L-ORD-01",
    unitSlug: "ord",
    lessonSlug: "sorting",
    assetPath: "/_internal/l-ord-01.html",
    defaultPb: "PB-32",
    problems: ["PB-32", "PB-109"],
    labs: ["ord01-order-relation", "ord01-comparator-contract", "ord01-sort-budget", "ord01-stability"]
  },
  "ord/struct-pair": {
    unitId: "U-ORD",
    lessonId: "L-ORD-02",
    unitSlug: "ord",
    lessonSlug: "struct-pair",
    assetPath: "/_internal/l-ord-02.html",
    defaultPb: "PB-112",
    problems: ["PB-112", "PB-169"],
    labs: ["ord02-record-mapper", "ord02-comparator-stepper", "ord02-stable-regression", "ord02-derived-key-overflow"]
  },
  "ord/map-set": {
    unitId: "U-ORD",
    lessonId: "L-ORD-03",
    unitSlug: "ord",
    lessonSlug: "map-set",
    assetPath: "/_internal/l-ord-03.html",
    defaultPb: "PB-47",
    problems: ["PB-47", "PB-91", "PB-50"],
    labs: ["ord03-association-mapper", "ord03-map-state", "ord03-container-choice"]
  },
  "pfx/prefix-sum": {
    unitId: "U-PFX",
    lessonId: "L-PFX-01",
    unitSlug: "pfx",
    lessonSlug: "prefix-sum",
    assetPath: "/_internal/l-pfx-01.html",
    defaultPb: "PB-93",
    problems: ["PB-93", "PB-25", "PB-76"],
    labs: [
      "complexity",
      "boundary",
      "range-cancellation",
      "micro-practice",
      "code-state-stepper",
      "index-conversion",
      "testcase-lab",
      "bug-hunt",
      "method-choice",
      "exit-console"
    ]
  },
  "pfx/prefix-relations": {
    unitId: "U-PFX",
    lessonId: "L-PFX-02",
    unitSlug: "pfx",
    lessonSlug: "prefix-relations",
    assetPath: "/_internal/l-pfx-02.html",
    defaultPb: "PB-90",
    problems: ["PB-90", "PB-61"],
    labs: ["pfx02-state-pair-mapper", "pfx02-frequency-stream", "pfx02-zero-order-bughunt"]
  },
  "pfx/prefix-2d": {
    unitId: "U-PFX",
    lessonId: "L-PFX-03",
    unitSlug: "pfx",
    lessonSlug: "prefix-2d",
    assetPath: "/_internal/l-pfx-03.html",
    defaultPb: "PB-140",
    problems: ["PB-140", "PB-77"],
    labs: ["pfx03-rectangle-ie", "pfx03-build-stepper", "pfx03-index-mapper"]
  },
  "pfx/difference-array": {
    unitId: "U-PFX",
    lessonId: "L-PFX-04",
    unitSlug: "pfx",
    lessonSlug: "difference-array",
    assetPath: "/_internal/l-pfx-04.html",
    defaultPb: "PB-21",
    problems: ["PB-21", "PB-134", "PB-135"],
    labs: ["pfx04-endpoint-simulator", "pfx04-interval-router", "pfx04-endpoint-bughunt"]
  },
  "win/two-pointers": {
    unitId: "U-WIN",
    lessonId: "L-WIN-01",
    unitSlug: "win",
    lessonSlug: "two-pointers",
    assetPath: "/_internal/l-win-01.html",
    defaultPb: "PB-94",
    problems: ["PB-94", "PB-48"],
    labs: ["win01-pointer-movement", "win01-discard-proof", "win01-crossing-bughunt"]
  },
  "win/sliding-window": {
    unitId: "U-WIN",
    lessonId: "L-WIN-02",
    unitSlug: "win",
    lessonSlug: "sliding-window",
    assetPath: "/_internal/l-win-02.html",
    defaultPb: "PB-78",
    problems: ["PB-78", "PB-80", "PB-101", "PB-100"],
    labs: ["win02-fixed-rolling", "win02-expand-shrink", "win02-window-state"]
  },
  "win/window-boundaries": {
    unitId: "U-WIN",
    lessonId: "L-WIN-03",
    unitSlug: "win",
    lessonSlug: "window-boundaries",
    assetPath: "/_internal/l-win-03.html",
    defaultPb: "PB-104",
    problems: ["PB-104"],
    labs: ["win03-negative-counterexample", "win03-monotonicity-checker", "win03-method-router"]
  },
  "bin/exact-search": {
    unitId: "U-BIN",
    lessonId: "L-BIN-01",
    unitSlug: "bin",
    lessonSlug: "exact-search",
    assetPath: "/_internal/l-bin-01.html",
    defaultPb: "PB-92",
    problems: ["PB-92", "PB-27", "PB-24"],
    labs: ["bin01-interval-trace", "bin01-mid-update", "bin01-termination-bughunt"]
  },
  "bin/boundary-search": {
    unitId: "U-BIN",
    lessonId: "L-BIN-02",
    unitSlug: "bin",
    lessonSlug: "boundary-search",
    assetPath: "/_internal/l-bin-02.html",
    defaultPb: "PB-103",
    problems: ["PB-103", "PB-95", "PB-102"],
    labs: ["bin02-first-true", "bin02-lower-upper", "bin02-duplicate-boundary"]
  },
  "bin/search-on-answer": {
    unitId: "U-BIN",
    lessonId: "L-BIN-03",
    unitSlug: "bin",
    lessonSlug: "search-on-answer",
    assetPath: "/_internal/l-bin-03.html",
    defaultPb: "PB-87",
    problems: ["PB-87", "PB-58"],
    labs: ["bin03-predicate-mapper", "bin03-monotonicity-checker", "bin03-bound-overflow"]
  },
  "rec/recursion-divide-conquer": {
    unitId: "U-REC",
    lessonId: "L-REC-01",
    unitSlug: "rec",
    lessonSlug: "recursion-divide-conquer",
    assetPath: "/_internal/l-rec-01.html",
    defaultPb: "PB-35",
    problems: ["PB-35", "PB-43"],
    labs: ["rec01-call-stack-stepper", "rec01-recursion-tree", "rec01-basecase-bughunt"]
  },
  "rec/expression-parsing": {
    unitId: "U-REC",
    lessonId: "L-REC-02",
    unitSlug: "rec",
    lessonSlug: "expression-parsing",
    assetPath: "/_internal/l-rec-02.html",
    defaultPb: "PB-18",
    problems: ["PB-18", "PB-141"],
    labs: ["rec02-token-cursor", "rec02-grammar-descent", "rec02-precedence-bughunt"]
  },
  "rec/backtracking": {
    unitId: "U-REC",
    lessonId: "L-REC-03",
    unitSlug: "rec",
    lessonSlug: "backtracking",
    assetPath: "/_internal/l-rec-03.html",
    defaultPb: "PB-44",
    problems: ["PB-44"],
    labs: ["rec03-search-tree-builder", "rec03-choose-undo-stepper", "rec03-state-divergence-bughunt"]
  },
  "rec/pruning-state": {
    unitId: "U-REC",
    lessonId: "L-REC-04",
    unitSlug: "rec",
    lessonSlug: "pruning-state",
    assetPath: "/_internal/l-rec-04.html",
    defaultPb: "PB-46",
    problems: ["PB-46", "PB-28"],
    labs: ["rec04-pruning-proof-builder", "rec04-state-lifetime-stepper", "rec04-search-space-counter"]
  },
  "rec/bitmask-state": {
    unitId: "U-REC",
    lessonId: "L-REC-05",
    unitSlug: "rec",
    lessonSlug: "bitmask-state",
    assetPath: "/_internal/l-rec-05.html",
    defaultPb: "PB-136",
    problems: ["PB-136", "PB-45"],
    labs: ["rec05-bit-switchboard", "rec05-mask-subset-mapper", "rec05-shift-boundary-bughunt"]
  },
  "ds/stack-queue-deque": {
    unitId: "U-DS",
    lessonId: "L-DS-01",
    unitSlug: "ds",
    lessonSlug: "stack-queue-deque",
    assetPath: "/_internal/l-ds-01.html",
    defaultPb: "PB-23",
    problems: ["PB-23", "PB-4"],
    labs: ["ds01-ordering-simulator", "ds01-operation-trace", "ds01-empty-api-bughunt"]
  },
  "ds/linear-ds": {
    unitId: "U-DS",
    lessonId: "L-DS-02",
    unitSlug: "ds",
    lessonSlug: "linear-ds",
    assetPath: "/_internal/l-ds-02.html",
    defaultPb: "PB-81",
    problems: ["PB-81", "PB-60", "PB-137"],
    labs: ["ds02-candidate-stack-visualizer", "ds02-deque-expire-dominate", "ds02-amortized-pop-counter"]
  },
  "ds/priority-queue": {
    unitId: "U-DS",
    lessonId: "L-DS-03",
    unitSlug: "ds",
    lessonSlug: "priority-queue",
    assetPath: "/_internal/l-ds-03.html",
    defaultPb: "PB-138",
    problems: ["PB-138"],
    labs: ["ds03-heap-ordering-visualizer", "ds03-topk-bounded-stepper", "ds03-comparator-bughunt"]
  },
  "gph/graph-tree-modeling": {
    unitId: "U-GPH",
    lessonId: "L-GPH-01",
    unitSlug: "gph",
    lessonSlug: "graph-tree-modeling",
    assetPath: "/_internal/l-gph-01.html",
    defaultPb: "PB-2",
    problems: ["PB-2"],
    labs: ["gph01-model-mapper", "gph01-adj-builder", "gph01-direction-bughunt"]
  },
  "gph/dfs": {
    unitId: "U-GPH",
    lessonId: "L-GPH-02",
    unitSlug: "gph",
    lessonSlug: "dfs",
    assetPath: "/_internal/l-gph-02.html",
    defaultPb: "PB-6",
    problems: ["PB-6", "PB-67"],
    labs: ["gph02-dfs-stack-trace", "gph02-component-floodfill", "gph02-visited-bughunt"]
  },
  "gph/bfs": {
    unitId: "U-GPH",
    lessonId: "L-GPH-03",
    unitSlug: "gph",
    lessonSlug: "bfs",
    assetPath: "/_internal/l-gph-03.html",
    defaultPb: "PB-68",
    problems: ["PB-68", "PB-69", "PB-12"],
    labs: ["gph03-layer-queue-stepper", "gph03-parent-reconstruct", "gph03-multisource-frontier"]
  },
  "gph/tree-state": {
    unitId: "U-GPH",
    lessonId: "L-GPH-04",
    unitSlug: "gph",
    lessonSlug: "tree-state",
    assetPath: "/_internal/l-gph-04.html",
    defaultPb: "PB-107",
    problems: ["PB-107", "PB-126", "PB-33"],
    labs: ["gph04-root-parent-depth", "gph04-subtree-combine", "gph04-tree-validity-bughunt"]
  },
  "grd/greedy-choice": {
    unitId: "U-GRD",
    lessonId: "L-GRD-01",
    unitSlug: "grd",
    lessonSlug: "greedy-choice",
    assetPath: "/_internal/l-grd-01.html",
    defaultPb: "PB-111",
    problems: ["PB-111", "PB-36", "PB-49"],
    labs: ["grd01-criterion-counterexample", "grd01-pairing-exchange", "grd01-greedy-or-not"]
  },
  "grd/sort-and-greedy": {
    unitId: "U-GRD",
    lessonId: "L-GRD-02",
    unitSlug: "grd",
    lessonSlug: "sort-and-greedy",
    assetPath: "/_internal/l-grd-02.html",
    defaultPb: "PB-99",
    problems: ["PB-99", "PB-52", "PB-57"],
    labs: ["grd02-sortkey-simulator", "grd02-interval-timeline", "grd02-resource-reuse-heap"]
  },
  "grd/greedy-correctness": {
    unitId: "U-GRD",
    lessonId: "L-GRD-03",
    unitSlug: "grd",
    lessonSlug: "greedy-correctness",
    assetPath: "/_internal/l-grd-03.html",
    defaultPb: "PB-54",
    problems: ["PB-54", "PB-123", "PB-8"],
    labs: ["grd03-exchange-swap-lab", "grd03-invariant-timeline", "grd03-proof-bughunt"]
  },
  "dp/dp-modeling": {
    unitId: "U-DP",
    lessonId: "L-DP-01",
    unitSlug: "dp",
    lessonSlug: "dp-modeling",
    assetPath: "/_internal/l-dp-01.html",
    defaultPb: "PB-63",
    problems: ["PB-63", "PB-84"],
    labs: ["dp01-repeated-subproblem-tree", "dp01-five-question-state-builder", "dp01-order-base-bughunt"]
  },
  "dp/standard-dp": {
    unitId: "U-DP",
    lessonId: "L-DP-02",
    unitSlug: "dp",
    lessonSlug: "standard-dp",
    assetPath: "/_internal/l-dp-02.html",
    defaultPb: "PB-64",
    problems: ["PB-64", "PB-129"],
    labs: ["dp02-cell-semantics-grid", "dp02-transition-arrow-builder", "dp02-order-sentinel-bughunt"]
  },
  "dp/knapsack": {
    unitId: "U-DP",
    lessonId: "L-DP-03",
    unitSlug: "dp",
    lessonSlug: "knapsack",
    assetPath: "/_internal/l-dp-03.html",
    defaultPb: "PB-39",
    problems: ["PB-39", "PB-65", "PB-17"],
    labs: ["dp03-two-layer-to-one-layer", "dp03-iteration-direction-stepper", "dp03-knapsack-bughunt"]
  },
  "dp/lis": {
    unitId: "U-DP",
    lessonId: "L-DP-04",
    unitSlug: "dp",
    lessonSlug: "lis",
    assetPath: "/_internal/l-dp-04.html",
    defaultPb: "PB-89",
    problems: ["PB-89", "PB-66", "PB-5"],
    labs: ["dp04-n2-predecessor-map", "dp04-tails-replacement-stepper", "dp04-lis-boundary-bughunt"]
  },
  "rng/coordinate-compression": {
    unitId: "U-RNG",
    lessonId: "L-RNG-01",
    unitSlug: "rng",
    lessonSlug: "coordinate-compression",
    assetPath: "/_internal/l-rng-01.html",
    defaultPb: "PB-173",
    problems: ["PB-173"],
    labs: ["rng01-order-vs-distance", "rng01-compression-mapper", "rng01-rank-bughunt"]
  },
  "rng/offline-counting": {
    unitId: "U-RNG",
    lessonId: "L-RNG-02",
    unitSlug: "rng",
    lessonSlug: "offline-counting",
    assetPath: "/_internal/l-rng-02.html",
    defaultPb: "PB-174",
    problems: ["PB-174"],
    labs: ["rng02-event-order-timeline", "rng02-tie-order-bughunt", "rng02-active-set-trace"]
  },
  "rng/range-trees": {
    unitId: "U-RNG",
    lessonId: "L-RNG-03",
    unitSlug: "rng",
    lessonSlug: "range-trees",
    assetPath: "/_internal/l-rng-03.html",
    defaultPb: "PB-175",
    problems: ["PB-175"],
    labs: ["rng03-prefix-to-tree-motivation", "rng03-fenwick-lowbit-path", "rng03-range-tree-bughunt"]
  },
  "rng/divide-conquer-counting": {
    unitId: "U-RNG",
    lessonId: "L-RNG-04",
    unitSlug: "rng",
    lessonSlug: "divide-conquer-counting",
    assetPath: "/_internal/l-rng-04.html",
    defaultPb: "PB-176",
    problems: ["PB-176"],
    labs: ["rng04-cross-pair-visualizer", "rng04-merge-count-stepper", "rng04-merge-invariant-bughunt"]
  },
  "mix/subtasks-strategy": {
    unitId: "U-MIX",
    lessonId: "L-MIX-01",
    unitSlug: "mix",
    lessonSlug: "subtasks-strategy",
    assetPath: "/_internal/l-mix-01.html",
    defaultPb: "PB-119",
    problems: ["PB-119"],
    labs: ["mix01-constraint-budget-board", "mix01-baseline-bottleneck-mapper", "mix01-score-strategy-scenarios"]
  },
  "mix/unfamiliar-modeling": {
    unitId: "U-MIX",
    lessonId: "L-MIX-02",
    unitSlug: "mix",
    lessonSlug: "unfamiliar-modeling",
    assetPath: "/_internal/l-mix-02.html",
    defaultPb: "PB-71",
    problems: ["PB-71", "PB-117"],
    labs: ["mix02-representation-switchboard", "mix02-method-evidence-mapper", "mix02-method-choice-bughunt"]
  },
  "mix/contest-debugging": {
    unitId: "U-MIX",
    lessonId: "L-MIX-03",
    unitSlug: "mix",
    lessonSlug: "contest-debugging",
    assetPath: "/_internal/l-mix-03.html",
    defaultPb: "PB-125",
    problems: ["PB-125", "PB-116"],
    labs: ["mix03-testcase-factory", "mix03-first-divergence-tracer", "mix03-contest-triage-simulator"]
  },
  "mix/final-readiness": {
    unitId: "U-MIX",
    lessonId: "L-MIX-04",
    unitSlug: "mix",
    lessonSlug: "final-readiness",
    assetPath: "/_internal/l-mix-04.html",
    defaultPb: "",
    problems: [],
    labs: ["mix04-evidence-portfolio-board", "mix04-critical-gap-detector", "mix04-readiness-claim-bughunt"]
  }
};
function resolveSemanticPath(pathname) {
  if (!pathname.startsWith("/learn/")) return null;
  const parts = pathname.split("/").filter(Boolean);
  if (parts[0] !== "learn") return null;
  if (parts.length < 3) return { kind: "invalid", reason: "INVALID_LESSON_PATH" };
  const key = `${parts[1]}/${parts[2]}`;
  const lesson = LESSON_ROUTES[key];
  if (!lesson) return { kind: "invalid", reason: "UNKNOWN_LESSON" };
  if (parts.length === 3) return { kind: "lesson", lesson };
  if (parts.length === 5 && parts[3] === "lab") {
    const labSlug = parts[4];
    return lesson.labs.includes(labSlug) ? { kind: "lab", lesson, labSlug } : { kind: "invalid", reason: "UNKNOWN_LAB" };
  }
  return { kind: "invalid", reason: "INVALID_LESSON_PATH" };
}
__name(resolveSemanticPath, "resolveSemanticPath");
function problemBelongsToLesson(lesson, pbUid) {
  return lesson.problems.includes(pbUid);
}
__name(problemBelongsToLesson, "problemBelongsToLesson");

// src/index.ts
var NOTION_API = "https://api.notion.com/v1";
var NOTION_VERSION = "2026-03-11";
var REC_DS = "36a43be9-58cd-8015-88d3-000ba21d3afc";
var SKILL_DS = "49e0d7dc-4902-4254-859f-03c617ebb2cf";
var PROBLEM_DS = "5e0d55cd-c617-4bf2-ac94-5e4e643e5aa6";
var EVIDENCE_DS = "0075c9be-b4d8-41c1-b933-bebd2ccda749";
var MAX_BODY_BYTES = 16384;
var ALLOWED_PROBLEMS = {
  "PB-93": "3c643be9-58cd-81b2-8d1b-c83e49f67d22",
  "PB-25": "3c643be9-58cd-8195-823c-f7af5c9e809e",
  "PB-76": "3c643be9-58cd-817c-8370-d3ec3a4253fc",
  "PB-142": "3c843be9-58cd-8148-b552-fb9eaed125b7",
  "PB-143": "3c843be9-58cd-819c-93e2-f7919b274f72",
  "PB-144": "3c843be9-58cd-81ec-8514-ec1bbff866e3",
  "PB-96": "3c643be9-58cd-812b-9a45-f15c3243df04",
  "PB-40": "3c643be9-58cd-8134-a8da-e7d5f4a2d361",
  "PB-20": "3c643be9-58cd-8170-8b5a-e24515b21473",
  "PB-145": "3c843be9-58cd-8131-b556-e8d14e0c781a",
  "PB-146": "3c843be9-58cd-814c-921f-d4a33b15fcca",
  "PB-151": "3c843be9-58cd-8169-88ef-e4420013ea9e",
  "PB-147": "3c843be9-58cd-81a0-9b8d-ea557aa7aa7d",
  "PB-148": "3c843be9-58cd-81ae-95d6-c4e4fdaa04d8",
  "PB-41": "3c643be9-58cd-81f7-bdeb-f87fc6588080",
  "PB-149": "3c843be9-58cd-814d-a010-dce2c26e82b1",
  "PB-150": "3c843be9-58cd-81e7-b723-c20f50f06607",
  "PB-152": "3c943be9-58cd-81a3-a9fd-f8a4e054785f",
  "PB-98": "3c643be9-58cd-8110-a218-cc30347f882e",
  "PB-153": "3c943be9-58cd-81ab-9dc8-eec807d2ecf0",
  "PB-97": "3c643be9-58cd-8112-afd3-e829a5f2f2b6",
  "PB-10": "3c643be9-58cd-813f-b446-f1dcf34b48bd",
  "PB-42": "3c643be9-58cd-8147-9fc2-f4ff269fa0a8",
  "PB-154": "3c943be9-58cd-816d-af61-f01c5258f408",
  "PB-37": "3c643be9-58cd-81e5-99ea-cdd74fead7c7",
  "PB-9": "3c643be9-58cd-8134-b28b-def25f8b9b00",
  "PB-155": "3c943be9-58cd-81df-809e-ef2c2a374512",
  "PB-114": "3c643be9-58cd-813f-b5d3-f02e4386e39c",
  "PB-120": "3c643be9-58cd-819a-8c2a-f7e6a44b7c2a",
  "PB-115": "3c643be9-58cd-8167-b178-f2fd2f4a1e1f",
  "PB-156": "3c943be9-58cd-81f8-87e1-db5db5f8df15",
  "PB-157": "3c943be9-58cd-8150-a52c-c4b9fbbc8c50",
  "PB-158": "3c943be9-58cd-811c-9fe5-e1eb2bc5450b",
  "PB-159": "3c943be9-58cd-81dd-be28-c0d3e6b7b1cb",
  "PB-160": "3c943be9-58cd-8176-8f2b-ebea9b2b912f",
  "PB-161": "3c943be9-58cd-81df-8a69-c3d10bb05330",
  "PB-162": "3c943be9-58cd-812a-8faf-f4f5ee725506",
  "PB-163": "3c943be9-58cd-8116-ae73-e73350cfcc15",
  "PB-164": "3c943be9-58cd-81ca-8efc-eae2242050e6",
  "PB-165": "3c943be9-58cd-81b7-ad0a-e6ffab0aca3e",
  "PB-166": "3c943be9-58cd-81a7-9467-feb11f71a016",
  "PB-167": "3c943be9-58cd-81a7-a64d-dde64148220b",
  "PB-168": "3c943be9-58cd-81e2-a2cc-c95197adbc64",
  "PB-131": "3c643be9-58cd-8135-a8c9-cae57f3bd8e6",
  "PB-32": "3c643be9-58cd-81c8-8eec-f98c4ecd80f3",
  "PB-47": "3c643be9-58cd-81ad-a0ee-d16ef8a79d45",
  "PB-50": "3c643be9-58cd-818d-8adb-fc28431d74d6",
  "PB-91": "3c643be9-58cd-817f-916e-dd80a8b60a50",
  "PB-109": "3c643be9-58cd-8116-91f0-e5be94acf6f8",
  "PB-112": "3c643be9-58cd-81c4-9034-d84805f5db6b",
  "PB-169": "3cb43be9-58cd-81b6-aaae-e1e261a48cca",
  "PB-90": "3c643be9-58cd-81a9-b251-fb72494f4716",
  "PB-61": "3c643be9-58cd-8106-9cc2-c2e667f04b74",
  "PB-140": "3c643be9-58cd-8174-8152-f61d384a4a1d",
  "PB-77": "3c643be9-58cd-81aa-b460-d89c09bd4672",
  "PB-21": "3c643be9-58cd-8179-bc06-ff930101f4b1",
  "PB-134": "3c643be9-58cd-81e4-9591-efc9955abb8e",
  "PB-135": "3c643be9-58cd-8109-b96a-c34120d4f3a1",
  "PB-94": "3c643be9-58cd-81d8-aa8a-e94617eafeeb",
  "PB-48": "3c643be9-58cd-81c3-8f14-f701f8f35cef",
  "PB-78": "3c643be9-58cd-8194-ab72-e3327caa5b19",
  "PB-80": "3c643be9-58cd-81fe-ba36-c962be7d3771",
  "PB-101": "3c643be9-58cd-81dc-8cea-c29365923675",
  "PB-100": "3c643be9-58cd-8126-81a2-e4e38bf34af1",
  "PB-104": "3c643be9-58cd-8179-a07b-fbc2797bf2e4",
  "PB-92": "3c643be9-58cd-8107-861b-c9c964203b64",
  "PB-27": "3c643be9-58cd-819b-bb1b-f594726a90bb",
  "PB-24": "3c643be9-58cd-8190-b12f-cd480ea94fa2",
  "PB-103": "3c643be9-58cd-8196-8178-c48ec181da3d",
  "PB-95": "3c643be9-58cd-8114-9f00-eeb5e4f92bc2",
  "PB-102": "3c643be9-58cd-812f-90c0-ebd78f9395ab",
  "PB-87": "3c643be9-58cd-8158-bac3-ec3d8456db0a",
  "PB-58": "3c643be9-58cd-8191-be96-fb3f9134fa22",
  "PB-35": "3c643be9-58cd-81de-8e58-fbc9ad483797",
  "PB-43": "3c643be9-58cd-811f-91fc-e29060de7f28",
  "PB-18": "3c643be9-58cd-8169-a82e-fa33e3e90460",
  "PB-141": "3c743be9-58cd-8178-b71d-c24e17413404",
  "PB-44": "3c643be9-58cd-81db-b4b3-e08378a7e87d",
  "PB-46": "3c643be9-58cd-8105-88f8-c43f204e9831",
  "PB-28": "3c643be9-58cd-81bc-b004-d0ad7f09c6b4",
  "PB-136": "3c643be9-58cd-8128-a25e-cb58070599fd",
  "PB-45": "3c643be9-58cd-81a4-8ad9-f9bc2ce81278",
  "PB-23": "3c643be9-58cd-8183-b139-c886ea104ef8",
  "PB-4": "3c643be9-58cd-810d-9d2d-fe9eab6ba286",
  "PB-81": "3c643be9-58cd-8113-ad61-c24c997c6fd8",
  "PB-60": "3c643be9-58cd-817f-87f5-d763963f633a",
  "PB-137": "3c643be9-58cd-8122-b2ed-c38ef7524cac",
  "PB-138": "3c643be9-58cd-81f1-b5bd-c58e1c2b6646",
  "PB-2": "3c643be9-58cd-8105-93d3-f441ddec5d51",
  "PB-6": "3c643be9-58cd-8113-9523-e63ab90d58c2",
  "PB-67": "3c643be9-58cd-8185-a1ff-e1fd3b1e781f",
  "PB-68": "3c643be9-58cd-81d8-99ef-edffbb28a0c2",
  "PB-69": "3c643be9-58cd-8104-a76d-f8392841f91e",
  "PB-12": "3c643be9-58cd-8148-85db-e2cb542862c7",
  "PB-107": "3c643be9-58cd-81de-a333-c539091b0904",
  "PB-126": "3c643be9-58cd-817e-b1d9-c94c21dcf202",
  "PB-33": "3c643be9-58cd-81cd-8d5d-eb672b96b236",
  "PB-111": "3c643be9-58cd-81b9-917e-f6608aa5c7b1",
  "PB-36": "3c643be9-58cd-81e1-bd4d-e951e5a1041f",
  "PB-49": "3c643be9-58cd-81ab-b585-ff6de92eb170",
  "PB-99": "3c643be9-58cd-81dc-a651-d02210e9e922",
  "PB-52": "3c643be9-58cd-8144-ab86-c2041e0be1ee",
  "PB-57": "3c643be9-58cd-81a3-92ca-da2c90119faf",
  "PB-54": "3c643be9-58cd-8116-af21-f793eb61caa0",
  "PB-123": "3c643be9-58cd-81f5-ba40-c9454996b78f",
  "PB-8": "3c643be9-58cd-812a-b659-efe281e47048",
  "PB-63": "3c643be9-58cd-8149-8b0d-e8c9b8fd948c",
  "PB-84": "3c643be9-58cd-811b-b29d-d747daba46cc",
  "PB-64": "3c643be9-58cd-8126-b67e-e8d7fd98a1d2",
  "PB-129": "3c643be9-58cd-8170-adf7-e4b27fc23706",
  "PB-39": "3c643be9-58cd-81f5-ab6f-ef96629e57eb",
  "PB-65": "3c643be9-58cd-819e-81e1-f501c9a2cfd3",
  "PB-17": "3c643be9-58cd-8163-9575-eda7e26ebb1e",
  "PB-89": "3c643be9-58cd-81b2-95ce-ca000cfce21a",
  "PB-66": "3c643be9-58cd-8127-af2b-cd859b8092af",
  "PB-5": "3c643be9-58cd-8112-8f5c-e8680045f89d",
  "PB-173": "3cb43be9-58cd-81ff-ae32-f8cf924a2276",
  "PB-174": "3cb43be9-58cd-81b6-8f66-ea66e9a2b1ef",
  "PB-175": "3cb43be9-58cd-8145-97d3-e85c8e263e96",
  "PB-176": "3cb43be9-58cd-815c-b5df-f538a1feee60",
  "PB-119": "3c643be9-58cd-81d4-9d6a-f5a152b716ba",
  "PB-71": "3c643be9-58cd-81a4-a7b1-efcb8c28afee",
  "PB-117": "3c643be9-58cd-817b-b0fa-ff7f2fc95975",
  "PB-125": "3c643be9-58cd-81bc-be2f-cc06c4ce35d6",
  "PB-116": "3c643be9-58cd-81f5-b560-c8fa6e130c71"
};
var RESULTS = /* @__PURE__ */ new Set(["\u672A\u63D0\u4EA4/\u672A\u77E5", "AC", "WA", "CE", "RE", "TLE", "MLE"]);
var ASSISTANCE = /* @__PURE__ */ new Set(["A0", "A1", "A2", "A3", "A4", "A5"]);
var STAGES = /* @__PURE__ */ new Set(["\u7B2C\u4E00\u6B21\u63A5\u89F8", "\u7406\u89E3\u89C0\u5FF5", "\u7368\u7ACB\u89E3\u984C", "\u9650\u6642\u5BE6\u6230", "\u8907\u7FD2\u9A57\u8B49"]);
var ERRORS = /* @__PURE__ */ new Set(["\u8B80\u984C", "\u6F14\u7B97\u6CD5", "\u8CC7\u6599\u7D50\u69CB", "\u908A\u754C\u689D\u4EF6", "\u8907\u96DC\u5EA6", "\u5BE6\u4F5CBug", "\u8A9E\u6CD5"]);
var REMOTE_WRITEBACK_SCHEMA = "v2.3-remote-writeback-1";
var REMOTE_RECEIPT_SCHEMA = "v2.3-remote-receipt-1";
var REMOTE_RESULTS = /* @__PURE__ */ new Set(["AC", "WA", "CE", "RE", "TLE", "MLE"]);
var REMOTE_TRACKS = /* @__PURE__ */ new Set(["Reading", "Implementation"]);
var REMOTE_OUTCOMES = /* @__PURE__ */ new Set(["PASS", "PARTIAL", "FAIL"]);
var REMOTE_ACTIVITIES = /* @__PURE__ */ new Set(["Concept Check", "Guided Drill", "Core Independent", "Transfer Challenge", "Review", "Diagnostic", "Mock"]);
var REMOTE_NOVELTY = {
  new: "New",
  seen: "Seen",
  delayed_retest: "Delayed Retest",
  transfer: "Transfer",
  mixed: "Mixed",
  same_problem_repeat: "Same Problem Repeat"
};
var REMOTE_LANGUAGES = { cpp: "C++", python: "Python" };
var SEMANTIC_HTML_HEADERS = {
  "Cache-Control": "no-cache, must-revalidate",
  "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors https://app.notion.com https://www.notion.so https://*.notion.so https://*.notion.site",
  "X-Robots-Tag": "noindex, nofollow",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()"
};
function htmlError(title, detail, status = 404) {
  const body = `<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${title}</title></head><body><main><h1>${title}</h1><p>${detail}</p></main></body></html>`;
  return new Response(body, { status, headers: { ...SEMANTIC_HTML_HEADERS, "Content-Type": "text/html; charset=utf-8" } });
}
__name(htmlError, "htmlError");
async function serveAsset(env, request, assetPath, routeHeaders = {}) {
  const assetUrl = new URL(request.url);
  assetUrl.pathname = assetPath;
  assetUrl.search = "";
  const assetRequest = new Request(assetUrl.toString(), { method: request.method, headers: request.headers });
  const assetResponse = await env.ASSETS.fetch(assetRequest);
  const headers = new Headers(assetResponse.headers);
  for (const [key, value] of Object.entries(SEMANTIC_HTML_HEADERS)) headers.set(key, value);
  for (const [key, value] of Object.entries(routeHeaders)) headers.set(key, value);
  return new Response(request.method === "HEAD" ? null : assetResponse.body, {
    status: assetResponse.status,
    statusText: assetResponse.statusText,
    headers
  });
}
__name(serveAsset, "serveAsset");
async function serveSemanticLesson(env, request, lesson, url) {
  const requestedPb = url.searchParams.get("pb")?.trim() || "";
  const resolvedPb = requestedPb && problemBelongsToLesson(lesson, requestedPb) ? requestedPb : lesson.defaultPb;
  const diagnostic = requestedPb && requestedPb !== resolvedPb ? "PB_NOT_IN_LESSON" : "OK";
  return serveAsset(env, request, lesson.assetPath, {
    "X-APCS-Unit": lesson.unitId,
    "X-APCS-Lesson": lesson.lessonId,
    "X-APCS-Resolved-PB": resolvedPb,
    "X-APCS-Route-Diagnostic": diagnostic
  });
}
__name(serveSemanticLesson, "serveSemanticLesson");
async function serveSemanticLab(env, request, lesson, labSlug) {
  return serveAsset(env, request, `/labs/${labSlug}.html`, {
    "X-APCS-Unit": lesson.unitId,
    "X-APCS-Lesson": lesson.lessonId,
    "X-APCS-Lab": labSlug
  });
}
__name(serveSemanticLab, "serveSemanticLab");
var API_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "no-store",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer"
};
function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: API_HEADERS });
}
__name(json, "json");
var LEGACY_V55_PB_MAP = {
  "PB-25": "PB-25",
  "ZJ-e339": "PB-25",
  "PB-76": "PB-76",
  "CSES-1646": "PB-76"
};
function legacyV55Redirect(url) {
  const rawPb = url.searchParams.get("pb")?.trim() || "";
  const canonicalPb = rawPb ? LEGACY_V55_PB_MAP[rawPb] : "PB-25";
  if (!canonicalPb) return null;
  const target = new URL(url.toString());
  target.pathname = "/learn/pfx/prefix-sum";
  target.searchParams.set("pb", canonicalPb);
  return target;
}
__name(legacyV55Redirect, "legacyV55Redirect");
function cleanText(v, max = 2e3) {
  return typeof v === "string" ? v.trim().slice(0, max) : "";
}
__name(cleanText, "cleanText");
function numberInRange(v, min, max, fallback) {
  const n = Number(v);
  return Number.isFinite(n) ? Math.max(min, Math.min(max, n)) : fallback;
}
__name(numberInRange, "numberInRange");
async function secureEqual(a, b) {
  const enc = new TextEncoder();
  const [ha, hb] = await Promise.all([
    crypto.subtle.digest("SHA-256", enc.encode(a)),
    crypto.subtle.digest("SHA-256", enc.encode(b))
  ]);
  const aa = new Uint8Array(ha);
  const bb = new Uint8Array(hb);
  let diff = 0;
  for (let i = 0; i < aa.length; i++) diff |= aa[i] ^ bb[i];
  return diff === 0;
}
__name(secureEqual, "secureEqual");
async function notionFetch(env, path, init = {}) {
  const res = await fetch(`${NOTION_API}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${env.NOTION_API_TOKEN}`,
      "Notion-Version": NOTION_VERSION,
      "Content-Type": "application/json",
      ...init.headers || {}
    }
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    console.error(JSON.stringify({
      event: "notion_error",
      status: res.status,
      code: body.code,
      message: body.message
    }));
    throw new Error(`Notion API ${res.status}: ${String(body.message || "request failed")}`);
  }
  return body;
}
__name(notionFetch, "notionFetch");
function propText(p) {
  const items = p?.title || p?.rich_text || [];
  return items.map((x) => x.plain_text ?? x.text?.content ?? "").join("").trim();
}
__name(propText, "propText");
function propSelect(p) {
  return p?.select?.name?.trim() || "";
}
__name(propSelect, "propSelect");
function propRelation(p) {
  return (p?.relation || []).map((x) => x.id || "").filter(Boolean);
}
__name(propRelation, "propRelation");
function propNumber(p) {
  return typeof p?.number === "number" && Number.isFinite(p.number) ? p.number : 0;
}
__name(propNumber, "propNumber");
function propCheckbox(p) {
  return p?.checkbox === true;
}
__name(propCheckbox, "propCheckbox");
function propMultiSelect(p) {
  return (p?.multi_select || []).map((x) => x.name?.trim() || "").filter(Boolean);
}
__name(propMultiSelect, "propMultiSelect");
function propDate(p) {
  return p?.date?.start?.trim() || "";
}
__name(propDate, "propDate");
function propUniqueId(p, fallbackPrefix = "ID") {
  const u = p?.unique_id;
  if (!u || typeof u.number !== "number") return "";
  return `${u.prefix || fallbackPrefix}-${u.number}`;
}
__name(propUniqueId, "propUniqueId");
function propUrl(p) {
  return p?.url?.trim() || "";
}
__name(propUrl, "propUrl");
async function queryDataSource(env, dataSourceId, body = {}, maxPages = 10) {
  const results = [];
  let cursor = null;
  for (let pageNo = 0; pageNo < maxPages; pageNo++) {
    const payload = { page_size: 100, ...body };
    if (cursor) payload.start_cursor = cursor;
    const response = await notionFetch(env, `/data_sources/${dataSourceId}/query`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
    results.push(...response.results || []);
    if (!response.has_more || !response.next_cursor) break;
    cursor = response.next_cursor;
  }
  return results;
}
__name(queryDataSource, "queryDataSource");
async function queryDataSourceAll(env, dataSourceId, body = {}) {
  const results = [];
  let cursor = null;
  for (let pageNo = 0; pageNo < 100; pageNo++) {
    const payload = { page_size: 100, ...body };
    if (cursor) payload.start_cursor = cursor;
    const response = await notionFetch(env, `/data_sources/${dataSourceId}/query`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
    results.push(...response.results || []);
    if (!response.has_more || !response.next_cursor) return results;
    cursor = response.next_cursor;
  }
  throw new Error(`AUDIT_QUERY_LIMIT_EXCEEDED:${dataSourceId}`);
}
__name(queryDataSourceAll, "queryDataSourceAll");
function percent(numerator, denominator) {
  if (!denominator) return 0;
  return Math.round(numerator / denominator * 1e3) / 10;
}
__name(percent, "percent");
function unitCode(raw) {
  return raw.trim().split(/\s+/)[0] || raw.trim();
}
__name(unitCode, "unitCode");
function distribution(values) {
  const out = {};
  for (let i = 0; i <= 5; i++) out[String(i)] = 0;
  for (const value of values) {
    const key = String(Math.max(0, Math.min(5, Math.round(value || 0))));
    out[key] = (out[key] || 0) + 1;
  }
  return out;
}
__name(distribution, "distribution");
async function buildVisualDashboard(env) {
  const [skillPages, evidencePages] = await Promise.all([
    queryDataSource(env, SKILL_DS, { sorts: [{ property: "Path Order", direction: "ascending" }] }, 3),
    queryDataSource(env, EVIDENCE_DS, { sorts: [{ property: "\u65E5\u671F", direction: "descending" }] }, 8)
  ]);
  const rawSkills = skillPages.map((page) => {
    const props = page.properties || {};
    return {
      id: page.id,
      uid: propText(props["Skill UID"]),
      name: propText(props["\u6280\u80FD"]),
      unit: unitCode(propSelect(props["\u8AB2\u7A0B\u55AE\u5143"])),
      pathStage: propSelect(props["Path Stage"]),
      pathOrder: propNumber(props["Path Order"]),
      status: propSelect(props["Skill Status"]),
      rm: propNumber(props["RM"]),
      im: propNumber(props["IM"]),
      relevance3: propSelect(props["3+3 Relevance"]),
      relevance5: propSelect(props["5+5 Relevance"]),
      evidenceSuitability: propSelect(props["Evidence Suitability"]),
      capabilities: propMultiSelect(props["\u80FD\u529B\u9762\u5411"]),
      prerequisiteIds: propRelation(props["\u524D\u7F6E\u6280\u80FD\u7BC0\u9EDE"]),
      conceptualRequirement: propText(props["Conceptual Requirement"]),
      implementationRequirement: propText(props["Implementation Requirement"]),
      recommendedProblemTypes: propText(props["Recommended Problem Types"]),
      readingMilestone: propSelect(props["Reading Milestone"]),
      implementationMilestone: propSelect(props["Implementation Milestone"])
    };
  }).filter((skill) => /^S\d{2}(?:_|$)/i.test(skill.uid));
  const uidById = new Map(rawSkills.map((skill) => [skill.id, skill.uid]));
  const dependentIds = /* @__PURE__ */ new Map();
  for (const skill of rawSkills) {
    for (const prereqId of skill.prerequisiteIds) {
      const list = dependentIds.get(prereqId) || [];
      list.push(skill.id);
      dependentIds.set(prereqId, list);
    }
  }
  const evidence = evidencePages.map((page) => {
    const props = page.properties || {};
    const skillIds = propRelation(props["Skill"]);
    return {
      id: page.id,
      date: propDate(props["\u65E5\u671F"]),
      track: propSelect(props["Track"]),
      activity: propSelect(props["Activity"]),
      outcome: propSelect(props["Outcome"]),
      assistance: propSelect(props["Assistance"]),
      independent: propCheckbox(props["Independent"]),
      novelty: propSelect(props["Novelty"]),
      timed: propCheckbox(props["Timed"]),
      validForGate: propCheckbox(props["Valid for Gate"]),
      accuracy: propNumber(props["Accuracy %"]),
      skillIds,
      skillUids: skillIds.map((id) => uidById.get(id) || "").filter(Boolean)
    };
  });
  const evidenceBySkill = /* @__PURE__ */ new Map();
  for (const ev of evidence) {
    for (const skillId of ev.skillIds) {
      const list = evidenceBySkill.get(skillId) || [];
      list.push(ev);
      evidenceBySkill.set(skillId, list);
    }
  }
  const skills = rawSkills.map((skill) => {
    const related = evidenceBySkill.get(skill.id) || [];
    return {
      id: skill.id,
      uid: skill.uid,
      code: (skill.uid.match(/^S\d{2}/i)?.[0] || skill.uid).toUpperCase(),
      name: skill.name,
      unit: skill.unit,
      pathStage: skill.pathStage,
      pathOrder: skill.pathOrder,
      status: skill.status,
      rm: skill.rm,
      im: skill.im,
      relevance3: skill.relevance3,
      relevance5: skill.relevance5,
      evidenceSuitability: skill.evidenceSuitability,
      capabilities: skill.capabilities,
      prerequisites: skill.prerequisiteIds.map((id) => uidById.get(id) || "").filter(Boolean),
      dependents: (dependentIds.get(skill.id) || []).map((id) => uidById.get(id) || "").filter(Boolean),
      conceptualRequirement: skill.conceptualRequirement,
      implementationRequirement: skill.implementationRequirement,
      recommendedProblemTypes: skill.recommendedProblemTypes,
      readingMilestone: skill.readingMilestone,
      implementationMilestone: skill.implementationMilestone,
      evidenceCount: related.length,
      gateEvidenceCount: related.filter((ev) => ev.validForGate).length,
      latestEvidenceDate: related.map((ev) => ev.date).filter(Boolean).sort().reverse()[0] || ""
    };
  }).sort((a, b) => a.pathOrder - b.pathOrder || a.uid.localeCompare(b.uid));
  const statusCounts = {};
  for (const skill of skills) statusCounts[skill.status || "Unknown"] = (statusCounts[skill.status || "Unknown"] || 0) + 1;
  const buildMilestone = /* @__PURE__ */ __name((label, relevanceKey) => {
    const required = skills.filter((skill) => skill[relevanceKey] === "Required");
    const reading = required.filter((skill) => skill.capabilities.includes("Reading"));
    const implementation = required.filter((skill) => skill.capabilities.includes("Implementation"));
    const readingVerified = reading.filter((skill) => skill.status === "Verified").length;
    const implementationVerified = implementation.filter((skill) => skill.status === "Verified").length;
    const gaps = required.filter((skill) => skill.status !== "Verified");
    const criticalState = gaps.some((skill) => skill.status === "Locked" || skill.status === "Review Due") ? "critical-gap" : gaps.length ? "incomplete" : "coverage-complete";
    const mockPass = evidence.filter((ev) => ev.validForGate && ev.activity === "Mock" && ev.outcome === "PASS" && ev.timed && ev.assistance === "A0");
    const delayedPass = evidence.filter((ev) => ev.validForGate && ev.novelty === "Delayed Retest" && ev.outcome === "PASS" && ev.assistance === "A0");
    return {
      label,
      authoritativeState: gaps.length ? "NOT READY" : "PROVISIONAL",
      authoritativeNote: "MEAS-v1 readiness cannot be auto-promoted to READY from coverage alone; designated benchmark + no critical gap remain authoritative.",
      criticalState,
      requiredCount: required.length,
      verifiedCount: required.length - gaps.length,
      verifiedCoverage: percent(required.length - gaps.length, required.length),
      reading: { required: reading.length, verified: readingVerified, coverage: percent(readingVerified, reading.length) },
      implementation: { required: implementation.length, verified: implementationVerified, coverage: percent(implementationVerified, implementation.length) },
      mockGateEvidenceCount: mockPass.length,
      delayedGateEvidenceCount: delayedPass.length,
      gaps: gaps.map((skill) => ({ uid: skill.uid, code: skill.code, name: skill.name, status: skill.status, rm: skill.rm, im: skill.im }))
    };
  }, "buildMilestone");
  const nextSkills = [...skills].sort((a, b) => {
    const priority = /* @__PURE__ */ __name((s) => s === "Review Due" ? 0 : s === "Learning" || s === "Practice" ? 1 : s === "Ready" ? 2 : s === "Locked" ? 4 : 3, "priority");
    return priority(a.status) - priority(b.status) || a.pathOrder - b.pathOrder;
  }).filter((skill) => skill.status !== "Verified").slice(0, 12).map((skill) => ({ uid: skill.uid, code: skill.code, name: skill.name, unit: skill.unit, status: skill.status, rm: skill.rm, im: skill.im }));
  return {
    ok: true,
    schema: "VIS-v1-full",
    generatedAt: (/* @__PURE__ */ new Date()).toISOString(),
    source: {
      skillMap: "Skill Map v3",
      evidence: "EV-v1",
      measurement: "MEAS-v1"
    },
    counts: {
      skills: skills.length,
      evidence: evidence.length,
      validGateEvidence: evidence.filter((ev) => ev.validForGate).length
    },
    summary: {
      statusCounts,
      rmDistribution: distribution(skills.map((skill) => skill.rm)),
      imDistribution: distribution(skills.map((skill) => skill.im)),
      reviewDue: skills.filter((skill) => skill.status === "Review Due").map((skill) => ({ uid: skill.uid, code: skill.code, name: skill.name, unit: skill.unit })),
      nextSkills
    },
    milestones: {
      apcs3: buildMilestone("APCS 3+3", "relevance3"),
      apcs5: buildMilestone("APCS 5+5", "relevance5")
    },
    skills,
    recentEvidence: evidence.slice(0, 12).map((ev) => ({
      id: ev.id,
      date: ev.date,
      track: ev.track,
      activity: ev.activity,
      outcome: ev.outcome,
      assistance: ev.assistance,
      independent: ev.independent,
      novelty: ev.novelty,
      timed: ev.timed,
      validForGate: ev.validForGate,
      accuracy: ev.accuracy,
      skillUids: ev.skillUids
    }))
  };
}
__name(buildVisualDashboard, "buildVisualDashboard");
async function buildProblemLadder(env, lessonId) {
  const safeLesson = lessonId.trim().slice(0, 40);
  if (!/^L-[A-Z]{2,3}-\d{2}$/i.test(safeLesson)) {
    return { ok: false, error: "INVALID_LESSON_ID", status: 400 };
  }
  const pages = await queryDataSource(env, PROBLEM_DS, {
    filter: { property: "Primary Lesson", rich_text: { equals: safeLesson.toUpperCase() } },
    sorts: [{ property: "Lesson Order", direction: "ascending" }]
  }, 3);
  const problems = pages.map((page) => {
    const props = page.properties || {};
    return {
      id: page.id,
      pbUid: propUniqueId(props["PB UID"], "PB"),
      problemId: propText(props["Problem ID"]),
      title: propText(props["\u984C\u76EE"]),
      role: propSelect(props["\u984C\u76EE\u89D2\u8272"]),
      difficulty: propSelect(props["\u96E3\u5EA6\uFF08D1-D5\uFF09"]) || propSelect(props["\u96E3\u5EA6\uFF08D1\u2013D5\uFF09"]),
      evidenceSuitability: propSelect(props["Evidence Suitability"]),
      suitability3: propSelect(props["3+3 Suitability"]),
      suitability5: propSelect(props["5+5 Suitability"]),
      placementQa: propSelect(props["Placement QA"]),
      order: propNumber(props["Lesson Order"]),
      source: propSelect(props["\u4F86\u6E90\u5E73\u53F0"]),
      judge: propSelect(props["\u4F5C\u7B54\u5E73\u53F0"]),
      url: propUrl(props["\u984C\u76EE\u9023\u7D50"]),
      skillIds: propRelation(props["\u6280\u80FD\u7BC0\u9EDE"])
    };
  }).sort((a, b) => a.order - b.order || a.pbUid.localeCompare(b.pbUid));
  return { ok: true, schema: "VIS-v1-full", lesson: safeLesson.toUpperCase(), problems };
}
__name(buildProblemLadder, "buildProblemLadder");
function detectCycle(skills) {
  const byId = new Map(skills.map((skill) => [skill.id, skill]));
  const state = /* @__PURE__ */ new Map();
  const stack = [];
  const cycle = [];
  const visit = /* @__PURE__ */ __name((id) => {
    const current = state.get(id) || 0;
    if (current === 1) {
      const index = stack.indexOf(id);
      const ids = index >= 0 ? stack.slice(index).concat(id) : [id, id];
      cycle.push(...ids.map((nodeId) => byId.get(nodeId)?.uid || nodeId));
      return true;
    }
    if (current === 2) return false;
    state.set(id, 1);
    stack.push(id);
    const skill = byId.get(id);
    if (skill) {
      for (const prerequisiteId of skill.prerequisiteIds) {
        if (byId.has(prerequisiteId) && visit(prerequisiteId)) return true;
      }
    }
    stack.pop();
    state.set(id, 2);
    return false;
  }, "visit");
  for (const skill of skills) {
    if ((state.get(skill.id) || 0) === 0 && visit(skill.id)) break;
  }
  return cycle;
}
__name(detectCycle, "detectCycle");
async function buildSystemIntegrityAudit(env) {
  const [skillPages, problemPages, evidencePages, recPages] = await Promise.all([
    queryDataSourceAll(env, SKILL_DS, { sorts: [{ property: "Path Order", direction: "ascending" }] }),
    queryDataSourceAll(env, PROBLEM_DS),
    queryDataSourceAll(env, EVIDENCE_DS),
    queryDataSourceAll(env, REC_DS)
  ]);
  const exceptions = [];
  const warnings = [];
  const add = /* @__PURE__ */ __name((area, code, id, detail) => exceptions.push({ area, code, id, detail }), "add");
  const warn = /* @__PURE__ */ __name((area, code, id, detail) => warnings.push({ area, code, id, detail }), "warn");
  const skills = skillPages.map((page) => {
    const props = page.properties || {};
    return {
      id: page.id,
      uid: propText(props["Skill UID"]),
      name: propText(props["\u6280\u80FD"]),
      pathStage: propSelect(props["Path Stage"]),
      pathOrder: propNumber(props["Path Order"]),
      relevance3: propSelect(props["3+3 Relevance"]),
      relevance5: propSelect(props["5+5 Relevance"]),
      prerequisiteIds: propRelation(props["\u524D\u7F6E\u6280\u80FD\u7BC0\u9EDE"])
    };
  }).filter((skill) => /^S\d{2}(?:_|$)/i.test(skill.uid));
  const skillById = new Map(skills.map((skill) => [skill.id, skill]));
  const skillUidSeen = /* @__PURE__ */ new Map();
  if (skills.length !== 39) add("skill", "SKILL_COUNT", "Skill Map v3", `expected=39 actual=${skills.length}`);
  for (const skill of skills) {
    if (!skill.uid) add("skill", "MISSING_UID", skill.id, skill.name);
    const previous = skillUidSeen.get(skill.uid);
    if (previous) add("skill", "DUPLICATE_UID", skill.uid, `${previous},${skill.id}`);
    else skillUidSeen.set(skill.uid, skill.id);
    if (skill.pathOrder <= 0) add("skill", "INVALID_PATH_ORDER", skill.uid, String(skill.pathOrder));
    for (const prerequisiteId of skill.prerequisiteIds) {
      if (!skillById.has(prerequisiteId)) add("skill", "DANGLING_PREREQUISITE", skill.uid, prerequisiteId);
      const prerequisite = skillById.get(prerequisiteId);
      if (prerequisite && skill.relevance5 === "Required" && prerequisite.relevance5 === "Extension") {
        add("skill", "REQUIRED_DEPENDS_ON_EXTENSION", skill.uid, prerequisite.uid);
      }
    }
  }
  const roots = skills.filter((skill) => skill.prerequisiteIds.length === 0);
  if (roots.length !== 1) add("skill", "ROOT_COUNT", "Skill Map v3", `expected=1 actual=${roots.length}`);
  const cycle = detectCycle(skills);
  if (cycle.length) add("skill", "PREREQUISITE_CYCLE", "Skill Map v3", cycle.join(" -> "));
  const problems = problemPages.map((page) => {
    const props = page.properties || {};
    return {
      id: page.id,
      pbUid: propUniqueId(props["PB UID"], "PB"),
      active: propSelect(props["\u6559\u6750\u72C0\u614B"]) === "Active",
      primaryLesson: propText(props["Primary Lesson"]),
      lessonOrder: propNumber(props["Lesson Order"]),
      placementQa: propSelect(props["Placement QA"]),
      role: propSelect(props["\u984C\u76EE\u89D2\u8272"]),
      difficulty: propSelect(props["\u96E3\u5EA6\uFF08D1-D5\uFF09"]) || propSelect(props["\u96E3\u5EA6\uFF08D1\u2013D5\uFF09"]),
      evidenceSuitability: propSelect(props["Evidence Suitability"]),
      skillIds: propRelation(props["\u6280\u80FD\u7BC0\u9EDE"])
    };
  });
  const problemById = new Map(problems.map((problem) => [problem.id, problem]));
  const pbUidSeen = /* @__PURE__ */ new Map();
  for (const problem of problems) {
    if (!problem.pbUid) add("problem", "MISSING_PB_UID", problem.id, "PB UID empty");
    const previous = pbUidSeen.get(problem.pbUid);
    if (previous) add("problem", "DUPLICATE_PB_UID", problem.pbUid, `${previous},${problem.id}`);
    else if (problem.pbUid) pbUidSeen.set(problem.pbUid, problem.id);
    for (const skillId of problem.skillIds) {
      if (!skillById.has(skillId)) add("problem", "DANGLING_SKILL_RELATION", problem.pbUid || problem.id, skillId);
    }
    if (problem.active) {
      const benchmarkMockOnly = problem.role === "Mock" && problem.evidenceSuitability === "Mock-only";
      if (benchmarkMockOnly) {
        if (problem.primaryLesson) add("problem", "MOCK_PRIMARY_LESSON_POLLUTION", problem.pbUid, problem.primaryLesson);
        if (problem.lessonOrder > 0) add("problem", "MOCK_LESSON_ORDER_POLLUTION", problem.pbUid, String(problem.lessonOrder));
      } else {
        if (!/^L-[A-Z]{2,3}-(?:X)?\d{2}$/i.test(problem.primaryLesson)) add("problem", "ACTIVE_PRIMARY_LESSON", problem.pbUid, problem.primaryLesson || "empty");
        if (problem.lessonOrder <= 0) add("problem", "ACTIVE_LESSON_ORDER", problem.pbUid, String(problem.lessonOrder));
      }
      if (problem.placementQa !== "PASS") add("problem", "ACTIVE_PLACEMENT_QA", problem.pbUid, problem.placementQa || "empty");
      if (!problem.role) add("problem", "ACTIVE_ROLE_MISSING", problem.pbUid, "\u984C\u76EE\u89D2\u8272 empty");
      if (!problem.difficulty) add("problem", "ACTIVE_DIFFICULTY_MISSING", problem.pbUid, "difficulty empty");
      if (!problem.evidenceSuitability) add("problem", "ACTIVE_EVIDENCE_SUITABILITY_MISSING", problem.pbUid, "Evidence Suitability empty");
      if (!problem.skillIds.length) add("problem", "ACTIVE_SKILL_RELATION_MISSING", problem.pbUid, "\u6280\u80FD\u7BC0\u9EDE empty");
    }
  }
  const recs = recPages.map((page) => {
    const props = page.properties || {};
    return {
      id: page.id,
      recUid: propUniqueId(props["REC UID"], "REC"),
      pbUid: propText(props["PB UID"]),
      writebackId: propText(props["Writeback ID"]),
      kind: propSelect(props["\u7D00\u9304\u6027\u8CEA"]),
      source: propSelect(props["\u7D00\u9304\u4F86\u6E90"]),
      problemIds: propRelation(props["\u984C\u5EAB\u984C\u76EE"]),
      skillIds: propRelation(props["\u6280\u80FD\u7BC0\u9EDE"])
    };
  });
  const recById = new Map(recs.map((record) => [record.id, record]));
  const writebackSeen = /* @__PURE__ */ new Map();
  for (const record of recs) {
    if (record.writebackId) {
      const previous = writebackSeen.get(record.writebackId);
      if (previous) add("record", "DUPLICATE_WRITEBACK_ID", record.recUid || record.id, `${record.writebackId}:${previous}`);
      else writebackSeen.set(record.writebackId, record.id);
    }
    for (const problemId of record.problemIds) if (!problemById.has(problemId)) add("record", "DANGLING_PROBLEM_RELATION", record.recUid || record.id, problemId);
    for (const skillId of record.skillIds) if (!skillById.has(skillId)) add("record", "DANGLING_SKILL_RELATION", record.recUid || record.id, skillId);
    if (record.kind === "\u7CFB\u7D71\u6E2C\u8A66") {
      if (record.problemIds.length || record.skillIds.length) add("record", "SYSTEM_TEST_RELATION_POLLUTION", record.recUid || record.id, `problem=${record.problemIds.length} skill=${record.skillIds.length}`);
    }
    if (record.kind === "\u6B63\u5F0F\u7D00\u9304" && (record.source === "HTML Direct" || record.source === "Coach Direct")) {
      if (!record.pbUid) add("record", "FORMAL_PB_UID_MISSING", record.recUid || record.id, record.source);
      if (record.problemIds.length !== 1) add("record", "FORMAL_PROBLEM_RELATION", record.recUid || record.id, `count=${record.problemIds.length}`);
      if (!record.skillIds.length) add("record", "FORMAL_SKILL_RELATION_MISSING", record.recUid || record.id, record.source);
      if (record.problemIds.length === 1) {
        const relatedPb = problemById.get(record.problemIds[0])?.pbUid || "";
        if (relatedPb && record.pbUid && relatedPb !== record.pbUid) add("record", "PB_UID_RELATION_MISMATCH", record.recUid || record.id, `${record.pbUid}!=${relatedPb}`);
      }
    } else if (record.kind === "\u6B63\u5F0F\u7D00\u9304" && (!record.problemIds.length || !record.skillIds.length)) {
      warn("record", "MANUAL_OR_LEGACY_RELATION_GAP", record.recUid || record.id, record.source || "unknown source");
    }
  }
  const evidences = evidencePages.map((page) => {
    const props = page.properties || {};
    return {
      id: page.id,
      evUid: propUniqueId(props["EV UID"], "EV"),
      eventId: propText(props["Event ID"]),
      date: propDate(props["\u65E5\u671F"]),
      track: propSelect(props["Track"]),
      activity: propSelect(props["Activity"]),
      outcome: propSelect(props["Outcome"]),
      assistance: propSelect(props["Assistance"]),
      novelty: propSelect(props["Novelty"]),
      independent: propCheckbox(props["Independent"]),
      validForGate: propCheckbox(props["Valid for Gate"]),
      skillIds: propRelation(props["Skill"]),
      problemIds: propRelation(props["Problem"]),
      solveRecordIds: propRelation(props["Solve Record"])
    };
  });
  const eventIdSeen = /* @__PURE__ */ new Map();
  for (const evidence of evidences) {
    if (evidence.eventId) {
      const previous = eventIdSeen.get(evidence.eventId);
      if (previous) add("evidence", "DUPLICATE_EVENT_ID", evidence.evUid || evidence.id, `${evidence.eventId}:${previous}`);
      else eventIdSeen.set(evidence.eventId, evidence.id);
    }
    if (!evidence.skillIds.length) add("evidence", "SKILL_RELATION_MISSING", evidence.evUid || evidence.id, "MEAS-v1 requires corresponding Skill");
    for (const skillId of evidence.skillIds) if (!skillById.has(skillId)) add("evidence", "DANGLING_SKILL_RELATION", evidence.evUid || evidence.id, skillId);
    for (const problemId of evidence.problemIds) if (!problemById.has(problemId)) add("evidence", "DANGLING_PROBLEM_RELATION", evidence.evUid || evidence.id, problemId);
    for (const recordId of evidence.solveRecordIds) if (!recById.has(recordId)) add("evidence", "DANGLING_SOLVE_RECORD_RELATION", evidence.evUid || evidence.id, recordId);
    if (evidence.validForGate) {
      const missing = [
        ["date", evidence.date],
        ["track", evidence.track],
        ["activity", evidence.activity],
        ["outcome", evidence.outcome],
        ["assistance", evidence.assistance],
        ["novelty", evidence.novelty]
      ].filter(([, value]) => !value).map(([name]) => name);
      if (missing.length) add("evidence", "GATE_FACTS_MISSING", evidence.evUid || evidence.id, missing.join(","));
    }
    if (evidence.independent && /^(A[2-5])$/.test(evidence.assistance)) {
      warn("evidence", "INDEPENDENCE_ASSISTANCE_REVIEW", evidence.evUid || evidence.id, evidence.assistance);
    }
  }
  const byArea = /* @__PURE__ */ __name((area) => exceptions.filter((item) => item.area === area).length, "byArea");
  const pass = exceptions.length === 0;
  return {
    ok: pass,
    schema: "APCS-GLOBAL-INTEGRITY-v1",
    generatedAt: (/* @__PURE__ */ new Date()).toISOString(),
    exhaustive: true,
    source: { skillMap: "Skill Map v3", problemBank: "Problem Bank v3", evidence: "EV-v1", records: "REC-v3.1" },
    counts: { skills: skills.length, problems: problems.length, activeProblems: problems.filter((p) => p.active).length, evidence: evidences.length, records: recs.length },
    gates: {
      skillPrerequisiteQa: byArea("skill") === 0 ? "PASS" : "FAIL",
      relationIntegrity: ["skill", "problem", "evidence", "record"].every((area) => byArea(area) === 0) ? "PASS" : "FAIL",
      problemBankQa: byArea("problem") === 0 ? "PASS" : "FAIL",
      evidenceQa: byArea("evidence") === 0 ? "PASS" : "FAIL",
      recordIntegrity: byArea("record") === 0 ? "PASS" : "FAIL"
    },
    exceptions,
    warnings,
    note: "Warnings require human review but do not fail structural integrity. This audit does not manufacture learner readiness or benchmark PASS."
  };
}
__name(buildSystemIntegrityAudit, "buildSystemIntegrityAudit");
async function visualReadAuthorized(request, env) {
  if (!env.WRITE_KEY) return false;
  const suppliedKey = request.headers.get("X-APCS-Write-Key") || "";
  if (!suppliedKey) return false;
  return secureEqual(suppliedKey, env.WRITE_KEY);
}
__name(visualReadAuthorized, "visualReadAuthorized");
function normalizeProblemTitle(problemId, rawTitle) {
  let t = rawTitle.trim();
  const variants = [problemId, problemId.replace(/^ZJ-/i, ""), problemId.replace(/^CSES-/i, "")].filter(Boolean).sort((a, b) => b.length - a.length);
  for (const v of variants) {
    const escaped = v.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    t = t.replace(new RegExp(`^${escaped}[\\s\uFF5C|:\uFF1A.\xB7\\-]+`, "i"), "").trim();
  }
  return t || rawTitle || problemId;
}
__name(normalizeProblemTitle, "normalizeProblemTitle");
function semanticProblemUrl(pbUid, requestOrigin) {
  for (const lesson of Object.values(LESSON_ROUTES)) {
    if (!problemBelongsToLesson(lesson, pbUid)) continue;
    return `${requestOrigin}/learn/${lesson.unitSlug}/${lesson.lessonSlug}?pb=${encodeURIComponent(pbUid)}`;
  }
  return "";
}
__name(semanticProblemUrl, "semanticProblemUrl");
async function getCanonicalProblem(env, pbUid, requestOrigin) {
  const problemPageId = ALLOWED_PROBLEMS[pbUid];
  const page = await notionFetch(env, `/pages/${problemPageId}`);
  const props = page.properties || {};
  const problemId = propText(props["Problem ID"]);
  const rawTitle = propText(props["\u984C\u76EE"]);
  const source = propSelect(props["\u4F86\u6E90\u5E73\u53F0"]);
  const judge = propSelect(props["\u4F5C\u7B54\u5E73\u53F0"]);
  const canonicalUrl = propUrl(props["\u984C\u76EE\u9023\u7D50"]);
  const customProblem = source === "Custom" || judge === "Custom";
  const url = canonicalUrl || (customProblem ? semanticProblemUrl(pbUid, requestOrigin) : "");
  const difficulty = propSelect(props["\u96E3\u5EA6\uFF08D1-D5\uFF09"]) || propSelect(props["\u96E3\u5EA6\uFF08D1\u2013D5\uFF09"]);
  const skillPageIds = propRelation(props["\u6280\u80FD\u7BC0\u9EDE"]);
  if (!problemId || !rawTitle || !source || !judge || !url || !difficulty) {
    console.error(JSON.stringify({ event: "canonical_problem_invalid", pb_uid: pbUid, custom_problem: customProblem, has_url: Boolean(url) }));
    throw new Error(`Canonical Problem Bank metadata incomplete for ${pbUid}`);
  }
  const shortTitle = normalizeProblemTitle(problemId, rawTitle);
  return {
    pbUid,
    problemPageId,
    problemId,
    shortTitle,
    displayTitle: `${problemId}\uFF5C${shortTitle}`,
    source,
    judge,
    url,
    difficulty,
    skillPageIds
  };
}
__name(getCanonicalProblem, "getCanonicalProblem");
function richText(content) {
  return content ? [{ type: "text", text: { content } }] : [];
}
__name(richText, "richText");
function makePageBody(p, data) {
  const summary = `${data.result} \xB7 ${data.assistance} \xB7 ${data.independent ? "\u7368\u7ACB\u5B8C\u6210" : "\u975E\u7368\u7ACB"} \xB7 ${data.timeMin} \u5206\u9418 \xB7 ${data.stage}`;
  const errorLine = data.errors.length ? data.errors.join("\u3001") : "\u7121\u6A19\u8A18";
  const reviewLine = /^\d{4}-\d{2}-\d{2}$/.test(data.reviewDate) ? data.reviewDate : "\u672A\u8A2D\u5B9A";
  return [
    {
      object: "block",
      type: "callout",
      callout: {
        icon: { type: "emoji", emoji: "\u{1F9FE}" },
        color: "blue_background",
        rich_text: richText(`${p.displayTitle}
${summary}`)
      }
    },
    {
      object: "block",
      type: "heading_2",
      heading_2: { rich_text: richText("\u672C\u6B21\u6838\u5FC3\u6536\u7A6B") }
    },
    {
      object: "block",
      type: "paragraph",
      paragraph: { rich_text: richText(data.takeaway || "\u5C1A\u672A\u586B\u5BEB\uFF1B\u4E4B\u5F8C\u8907\u7FD2\u6642\u88DC\u4E0A\u4E00\u53E5\u771F\u6B63\u80FD\u63D0\u9192\u81EA\u5DF1\u7684\u91CD\u9EDE\u3002") }
    },
    {
      object: "block",
      type: "heading_2",
      heading_2: { rich_text: richText("\u932F\u8AA4\u8207\u8907\u7FD2") }
    },
    {
      object: "block",
      type: "bulleted_list_item",
      bulleted_list_item: { rich_text: richText(`\u932F\u8AA4\u985E\u578B\uFF1A${errorLine}`) }
    },
    {
      object: "block",
      type: "bulleted_list_item",
      bulleted_list_item: { rich_text: richText(`\u5617\u8A66\u6B21\u6578\uFF1A${data.attempts}`) }
    },
    {
      object: "block",
      type: "bulleted_list_item",
      bulleted_list_item: { rich_text: richText(`\u8907\u7FD2\u65E5\u671F\uFF1A${reviewLine}`) }
    },
    {
      object: "block",
      type: "quote",
      quote: { rich_text: richText("\u9019\u7B46 REC \u53EA\u4EE3\u8868\u672C\u6B21 attempt\uFF1B\u662F\u5426\u5F62\u6210 Evidence \u6216 Mastery\uFF0C\u4ECD\u4F9D EV-v1 / MEAS-v1 Gate\u3002") }
    }
  ];
}
__name(makePageBody, "makePageBody");
function formatRecUid(page) {
  const u = page.properties?.["REC UID"]?.unique_id;
  if (!u || typeof u.number !== "number") return null;
  return `${u.prefix || "REC"}-${u.number}`;
}
__name(formatRecUid, "formatRecUid");
function awareIso(value) {
  if (typeof value !== "string") return false;
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value)) return false;
  return Number.isFinite(Date.parse(value));
}
__name(awareIso, "awareIso");
function sameSet(a, b) {
  const aa = [...new Set(a || [])].sort();
  const bb = [...new Set(b || [])].sort();
  return aa.length === bb.length && aa.every((value, index) => value === bb[index]);
}
__name(sameSet, "sameSet");
function remoteStage(attempt) {
  if (attempt.activity === "Review") return "複習驗證";
  if (attempt.activity === "Mock" || attempt.timed === true) return "限時實戰";
  if ((attempt.activity === "Core Independent" || attempt.activity === "Transfer Challenge") && attempt.independent === true) return "獨立解題";
  if (["Concept Check", "Guided Drill", "Core Independent", "Transfer Challenge", "Diagnostic"].includes(attempt.activity)) return "理解觀念";
  return "";
}
__name(remoteStage, "remoteStage");
function validateRemoteWriteback(body) {
  if (!body || body.schema_version !== REMOTE_WRITEBACK_SCHEMA) return { error: "INVALID_REMOTE_SCHEMA", status: 400 };
  const writebackId = cleanText(body.writeback_id, 100);
  if (!/^[A-Za-z0-9._:-]{8,100}$/.test(writebackId)) return { error: "INVALID_WRITEBACK_ID", status: 400 };
  const attempt = body.attempt;
  if (!attempt || typeof attempt !== "object" || Array.isArray(attempt)) return { error: "INVALID_ATTEMPT", status: 400 };
  if (cleanText(attempt.writeback_id, 100) !== writebackId) return { error: "WRITEBACK_ID_MISMATCH", status: 400 };
  const attemptId = cleanText(attempt.attempt_id, 100);
  if (!/^[A-Za-z0-9._:-]{8,100}$/.test(attemptId)) return { error: "INVALID_ATTEMPT_ID", status: 400 };
  const pbUid = cleanText(attempt.pb_uid, 20);
  if (!(pbUid in ALLOWED_PROBLEMS)) return { error: "UNKNOWN_PROBLEM", status: 400 };
  const problemId = cleanText(attempt.problem_id, 100);
  if (!problemId) return { error: "INVALID_PROBLEM_ID", status: 400 };
  const finishedAt = cleanText(attempt.finished_at, 80);
  if (!awareIso(finishedAt)) return { error: "INVALID_FINISHED_AT", status: 400 };
  const startedAt = attempt.started_at == null ? null : cleanText(attempt.started_at, 80);
  if (startedAt !== null && (!awareIso(startedAt) || Date.parse(startedAt) > Date.parse(finishedAt))) return { error: "INVALID_STARTED_AT", status: 400 };
  const judgeResult = cleanText(attempt.judge_result, 30);
  if (!REMOTE_RESULTS.has(judgeResult)) return { error: "INVALID_JUDGE_RESULT", status: 400 };
  const assistance = attempt.assistance == null ? null : cleanText(attempt.assistance, 10);
  if (assistance !== null && !ASSISTANCE.has(assistance)) return { error: "INVALID_ASSISTANCE", status: 400 };
  const independent = attempt.independent == null ? null : attempt.independent;
  if (independent !== null && typeof independent !== "boolean") return { error: "INVALID_INDEPENDENT", status: 400 };
  const timed = attempt.timed == null ? null : attempt.timed;
  if (timed !== null && typeof timed !== "boolean") return { error: "INVALID_TIMED", status: 400 };
  const attemptCount = attempt.attempt_count == null ? null : Number(attempt.attempt_count);
  if (attemptCount !== null && (!Number.isInteger(attemptCount) || attemptCount < 1 || attemptCount > 999)) return { error: "INVALID_ATTEMPT_COUNT", status: 400 };
  const activeMinutes = attempt.active_minutes == null ? null : Number(attempt.active_minutes);
  if (activeMinutes !== null && (!Number.isFinite(activeMinutes) || activeMinutes < 0 || activeMinutes > 1e4)) return { error: "INVALID_ACTIVE_MINUTES", status: 400 };
  const language = cleanText(attempt.language, 30).toLowerCase();
  const notionLanguage = REMOTE_LANGUAGES[language] || null;
  const novelty = attempt.novelty == null ? null : cleanText(attempt.novelty, 40);
  const notionNovelty = novelty === null ? null : REMOTE_NOVELTY[novelty];
  if (novelty !== null && !notionNovelty) return { error: "INVALID_NOVELTY", status: 400 };
  if (attempt.notion_novelty != null && cleanText(attempt.notion_novelty, 40) !== (notionNovelty || "")) return { error: "NOVELTY_PROJECTION_MISMATCH", status: 400 };
  if (attempt.notion_language != null && cleanText(attempt.notion_language, 30) !== (notionLanguage || "")) return { error: "LANGUAGE_PROJECTION_MISMATCH", status: 400 };
  if (attempt.source != null && cleanText(attempt.source, 40) !== "VS Code Direct") return { error: "INVALID_RECORD_SOURCE", status: 400 };
  const activity = attempt.activity == null ? null : cleanText(attempt.activity, 40);
  if (activity !== null && !REMOTE_ACTIVITIES.has(activity)) return { error: "INVALID_ACTIVITY", status: 400 };
  const evidence = Array.isArray(body.evidence) ? body.evidence : null;
  if (evidence === null || evidence.length > 16) return { error: "INVALID_EVIDENCE_ARRAY", status: 400 };
  const eventIds = new Set();
  const normalizedEvidence = [];
  for (const raw of evidence) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) return { error: "INVALID_EVIDENCE_EVENT", status: 400 };
    const eventId = cleanText(raw.event_id, 140);
    if (!/^[A-Za-z0-9._:-]{8,140}$/.test(eventId) || eventIds.has(eventId)) return { error: "INVALID_EVENT_ID", status: 400 };
    eventIds.add(eventId);
    if (cleanText(raw.writeback_id, 100) !== writebackId) return { error: "EVIDENCE_WRITEBACK_MISMATCH", status: 400 };
    if (cleanText(raw.pb_uid, 20) !== pbUid || cleanText(raw.problem_id, 100) !== problemId) return { error: "EVIDENCE_PROBLEM_MISMATCH", status: 400 };
    const skillUid = cleanText(raw.skill_uid, 100);
    if (!/^S\d{2}(?:_[A-Za-z0-9_]+)?$/.test(skillUid)) return { error: "INVALID_SKILL_UID", status: 400 };
    const track = cleanText(raw.track, 30);
    const outcome = cleanText(raw.outcome, 30);
    if (!REMOTE_TRACKS.has(track)) return { error: "INVALID_TRACK", status: 400 };
    if (!REMOTE_OUTCOMES.has(outcome)) return { error: "INVALID_OUTCOME", status: 400 };
    if (cleanText(raw.occurred_at, 80) !== finishedAt) return { error: "EVIDENCE_TIME_MISMATCH", status: 400 };
    if (cleanText(raw.judge_result, 30) !== judgeResult) return { error: "EVIDENCE_JUDGE_MISMATCH", status: 400 };
    if ((raw.assistance == null ? null : cleanText(raw.assistance, 10)) !== assistance) return { error: "EVIDENCE_ASSISTANCE_MISMATCH", status: 400 };
    if ((raw.independent == null ? null : raw.independent) !== independent) return { error: "EVIDENCE_INDEPENDENT_MISMATCH", status: 400 };
    if ((raw.timed == null ? null : raw.timed) !== timed) return { error: "EVIDENCE_TIMED_MISMATCH", status: 400 };
    if ((raw.active_minutes == null ? null : Number(raw.active_minutes)) !== activeMinutes) return { error: "EVIDENCE_TIME_MIN_MISMATCH", status: 400 };
    if ((raw.novelty == null ? null : cleanText(raw.novelty, 40)) !== novelty) return { error: "EVIDENCE_NOVELTY_MISMATCH", status: 400 };
    if ((raw.activity == null ? null : cleanText(raw.activity, 40)) !== activity) return { error: "EVIDENCE_ACTIVITY_MISMATCH", status: 400 };
    if (raw.notion_novelty != null && cleanText(raw.notion_novelty, 40) !== (notionNovelty || "")) return { error: "EVIDENCE_NOVELTY_PROJECTION_MISMATCH", status: 400 };
    normalizedEvidence.push({
      eventId,
      skillUid,
      track,
      outcome,
      note: cleanText(raw.note, 2e3)
    });
  }
  return {
    writebackId,
    attempt: {
      attemptId,
      pbUid,
      problemId,
      startedAt,
      finishedAt,
      language,
      notionLanguage,
      judgeResult,
      assistance,
      independent,
      attemptCount,
      activeMinutes,
      timed,
      novelty,
      notionNovelty,
      activity,
      note: cleanText(attempt.note, 2e3)
    },
    evidence: normalizedEvidence
  };
}
__name(validateRemoteWriteback, "validateRemoteWriteback");
async function resolveSkillPage(env, skillUid) {
  const response = await notionFetch(env, `/data_sources/${SKILL_DS}/query`, {
    method: "POST",
    body: JSON.stringify({
      filter: { property: "Skill UID", rich_text: { equals: skillUid } },
      page_size: 2
    })
  });
  if ((response.results || []).length !== 1) return { error: "SKILL_IDENTITY_NOT_UNIQUE", status: 409, skill_uid: skillUid };
  return { pageId: response.results[0].id };
}
__name(resolveSkillPage, "resolveSkillPage");
function remoteRecIdentityConflict(page, p, writebackId, skillPageIds) {
  const props = page.properties || {};
  if (propText(props["Writeback ID"]) !== writebackId) return true;
  if (propText(props["PB UID"]) !== p.pbUid) return true;
  if (propText(props["Problem ID"]) !== p.problemId) return true;
  if (propSelect(props["紀錄來源"]) !== "VS Code Direct") return true;
  if (propSelect(props["紀錄性質"]) !== "正式紀錄") return true;
  if (!sameSet(propRelation(props["題庫題目"]), [p.problemPageId])) return true;
  if (!sameSet(propRelation(props["技能節點"]), skillPageIds)) return true;
  return false;
}
__name(remoteRecIdentityConflict, "remoteRecIdentityConflict");
function remoteEvidenceIdentityConflict(page, expected) {
  const props = page.properties || {};
  if (propText(props["Event ID"]) !== expected.eventId) return true;
  if (propSelect(props["Track"]) !== expected.track) return true;
  if (propSelect(props["Outcome"]) !== expected.outcome) return true;
  if (!sameSet(propRelation(props["Problem"]), [expected.problemPageId])) return true;
  if (!sameSet(propRelation(props["Skill"]), [expected.skillPageId])) return true;
  if (!sameSet(propRelation(props["Solve Record"]), [expected.recPageId])) return true;
  return false;
}
__name(remoteEvidenceIdentityConflict, "remoteEvidenceIdentityConflict");
function makeRemoteRecBody(p, attempt) {
  const assistance = attempt.assistance || "Assistance unknown";
  const independent = attempt.independent === null ? "Independent unknown" : attempt.independent ? "獨立完成" : "非獨立";
  const time = attempt.activeMinutes === null ? "time unknown" : `${attempt.activeMinutes} 分鐘`;
  const stage = remoteStage(attempt) || "stage unknown";
  const summary = `${attempt.judgeResult} · ${assistance} · ${independent} · ${time} · ${stage}`;
  return [
    {
      object: "block",
      type: "callout",
      callout: { icon: { type: "emoji", emoji: "🧾" }, color: "green_background", rich_text: richText(`${p.displayTitle}\n${summary}`) }
    },
    {
      object: "block",
      type: "paragraph",
      paragraph: { rich_text: richText(attempt.note || "VS Code Direct durable attempt. Evidence / mastery remains governed by EV-v1 / MEAS-v1.") }
    }
  ];
}
__name(makeRemoteRecBody, "makeRemoteRecBody");
async function writeRemoteBundle(env, body, requestOrigin) {
  const parsed = validateRemoteWriteback(body);
  if ("error" in parsed) return parsed;
  const p = await getCanonicalProblem(env, parsed.attempt.pbUid, requestOrigin);
  if (p.problemId.toLowerCase() !== parsed.attempt.problemId.toLowerCase()) return { error: "CANONICAL_PROBLEM_ID_MISMATCH", status: 409 };
  const skillMap = /* @__PURE__ */ new Map();
  for (const event of parsed.evidence) {
    if (skillMap.has(event.skillUid)) continue;
    const resolved = await resolveSkillPage(env, event.skillUid);
    if ("error" in resolved) return resolved;
    skillMap.set(event.skillUid, resolved.pageId);
  }
  const skillPageIds = [...skillMap.values()].sort();
  const existingRec = await notionFetch(env, `/data_sources/${REC_DS}/query`, {
    method: "POST",
    body: JSON.stringify({ filter: { property: "Writeback ID", rich_text: { equals: parsed.writebackId } }, page_size: 2 })
  });
  if ((existingRec.results || []).length > 1) return { error: "DUPLICATE_WRITEBACK_ID", status: 409 };
  let recPage;
  let recDuplicate = false;
  if (existingRec.results?.length === 1) {
    recPage = existingRec.results[0];
    if (remoteRecIdentityConflict(recPage, p, parsed.writebackId, skillPageIds)) return { error: "WRITEBACK_IDENTITY_CONFLICT", status: 409 };
    recDuplicate = true;
  } else {
    const a = parsed.attempt;
    const properties = {
      "題目": { title: [{ text: { content: p.displayTitle } }] },
      "PB UID": { rich_text: [{ text: { content: p.pbUid } }] },
      "題庫題目": { relation: [{ id: p.problemPageId }] },
      "技能節點": { relation: skillPageIds.map((id) => ({ id })) },
      "Problem ID": { rich_text: [{ text: { content: p.problemId } }] },
      "來源平台": { select: { name: p.source } },
      "作答平台": { select: { name: p.judge } },
      "題目連結": { url: p.url },
      "難度（D1–D5）": { select: { name: p.difficulty } },
      "最新提交結果": { select: { name: a.judgeResult } },
      "Writeback ID": { rich_text: [{ text: { content: parsed.writebackId } }] },
      "紀錄來源": { select: { name: "VS Code Direct" } },
      "紀錄性質": { select: { name: "正式紀錄" } },
      "學習歷程候選": { checkbox: false },
      "Independent Known": { checkbox: a.independent !== null },
      "Attempt Finished At": { date: { start: a.finishedAt } }
    };
    if (a.startedAt !== null) properties["Attempt Started At"] = { date: { start: a.startedAt } };
    if (a.notionLanguage) properties["使用語言"] = { multi_select: [{ name: a.notionLanguage }] };
    if (a.assistance !== null) properties["Assistance"] = { select: { name: a.assistance } };
    if (a.independent !== null) properties["獨立完成"] = { checkbox: a.independent };
    if (a.attemptCount !== null) properties["嘗試次數"] = { number: a.attemptCount };
    if (a.activeMinutes !== null) properties["解題時間(分鐘)"] = { number: a.activeMinutes };
    const stage = remoteStage(a);
    if (stage) properties["學習階段"] = { select: { name: stage } };
    if (a.note) properties["核心收穫"] = { rich_text: [{ text: { content: a.note } }] };
    recPage = await notionFetch(env, "/pages", {
      method: "POST",
      body: JSON.stringify({
        parent: { type: "data_source_id", data_source_id: REC_DS },
        icon: { type: "emoji", emoji: "🧩" },
        properties,
        children: makeRemoteRecBody(p, a)
      })
    });
  }
  const evidenceReceipts = [];
  let createdEvidence = 0;
  for (const event of parsed.evidence) {
    const skillPageId = skillMap.get(event.skillUid);
    const existing = await notionFetch(env, `/data_sources/${EVIDENCE_DS}/query`, {
      method: "POST",
      body: JSON.stringify({ filter: { property: "Event ID", rich_text: { equals: event.eventId } }, page_size: 2 })
    });
    if ((existing.results || []).length > 1) return { error: "DUPLICATE_EVENT_ID", status: 409 };
    const expected = { ...event, problemPageId: p.problemPageId, skillPageId, recPageId: recPage.id };
    if (existing.results?.length === 1) {
      const page = existing.results[0];
      if (remoteEvidenceIdentityConflict(page, expected)) return { error: "EVENT_IDENTITY_CONFLICT", status: 409 };
      evidenceReceipts.push({ event_id: event.eventId, page_id: page.id, duplicate: true });
      continue;
    }
    const a = parsed.attempt;
    const properties = {
      "事件": { title: [{ text: { content: `${event.eventId} · ${event.skillUid} × ${event.track}` } }] },
      "Event ID": { rich_text: [{ text: { content: event.eventId } }] },
      "日期": { date: { start: a.finishedAt } },
      "Track": { select: { name: event.track } },
      "Outcome": { select: { name: event.outcome } },
      "Judge Result": { select: { name: a.judgeResult } },
      "Independent Known": { checkbox: a.independent !== null },
      "Timed Known": { checkbox: a.timed !== null },
      "Skill": { relation: [{ id: skillPageId }] },
      "Problem": { relation: [{ id: p.problemPageId }] },
      "Solve Record": { relation: [{ id: recPage.id }] }
    };
    if (a.activity !== null) properties["Activity"] = { select: { name: a.activity } };
    if (a.assistance !== null) properties["Assistance"] = { select: { name: a.assistance } };
    if (a.independent !== null) properties["Independent"] = { checkbox: a.independent };
    if (a.timed !== null) properties["Timed"] = { checkbox: a.timed };
    if (a.activeMinutes !== null) properties["Time min"] = { number: a.activeMinutes };
    if (a.notionNovelty !== null) properties["Novelty"] = { select: { name: a.notionNovelty } };
    if (event.note) properties["Evidence Note"] = { rich_text: [{ text: { content: event.note } }] };
    const page = await notionFetch(env, "/pages", {
      method: "POST",
      body: JSON.stringify({ parent: { type: "data_source_id", data_source_id: EVIDENCE_DS }, icon: { type: "emoji", emoji: "🧪" }, properties })
    });
    createdEvidence += 1;
    evidenceReceipts.push({ event_id: event.eventId, page_id: page.id, duplicate: false });
  }
  return {
    schema_version: REMOTE_RECEIPT_SCHEMA,
    writeback_id: parsed.writebackId,
    complete: true,
    rec: { page_id: recPage.id, duplicate: recDuplicate },
    evidence: evidenceReceipts,
    created: !recDuplicate || createdEvidence > 0
  };
}
__name(writeRemoteBundle, "writeRemoteBundle");

async function writeRecord(env, body, requestOrigin) {
  const pbUid = cleanText(body.pb_uid, 20);
  if (!(pbUid in ALLOWED_PROBLEMS)) return { error: "UNKNOWN_PROBLEM", status: 400 };
  const writebackId = cleanText(body.writeback_id, 100);
  if (!/^[A-Za-z0-9._:-]{8,100}$/.test(writebackId)) {
    return { error: "INVALID_WRITEBACK_ID", status: 400 };
  }
  const resultRaw = cleanText(body.latest_result, 30);
  const assistanceRaw = cleanText(body.assistance, 10);
  const stageRaw = cleanText(body.stage, 30);
  const result = RESULTS.has(resultRaw) ? resultRaw : "\u672A\u63D0\u4EA4/\u672A\u77E5";
  const assistance = ASSISTANCE.has(assistanceRaw) ? assistanceRaw : "A0";
  const stage = STAGES.has(stageRaw) ? stageRaw : "\u7B2C\u4E00\u6B21\u63A5\u89F8";
  const errors = Array.isArray(body.error_types) ? [...new Set(body.error_types.map((x) => cleanText(x, 30)).filter((x) => ERRORS.has(x)))] : [];
  const attempts = Math.round(numberInRange(body.attempts, 1, 999, 1));
  const timeMin = Math.round(numberInRange(body.time_min, 0, 1e4, 0) * 10) / 10;
  const takeaway = cleanText(body.core_takeaway, 2e3);
  const reviewDate = cleanText(body.review_date, 20);
  const independent = body.independent === true;
  const recordKind = body.record_kind === "system_test" ? "\u7CFB\u7D71\u6E2C\u8A66" : "\u6B63\u5F0F\u7D00\u9304";
  const existing = await notionFetch(env, `/data_sources/${REC_DS}/query`, {
    method: "POST",
    body: JSON.stringify({
      filter: { property: "Writeback ID", rich_text: { equals: writebackId } },
      page_size: 1
    })
  });
  if (existing.results?.length) {
    const page2 = existing.results[0];
    return {
      duplicate: true,
      page_id: page2.id,
      url: page2.url,
      writeback_id: writebackId,
      rec_uid: formatRecUid(page2)
    };
  }
  const p = await getCanonicalProblem(env, pbUid, requestOrigin);
  const formal = recordKind === "\u6B63\u5F0F\u7D00\u9304";
  const properties = {
    "\u984C\u76EE": { title: [{ text: { content: p.displayTitle } }] },
    "PB UID": { rich_text: [{ text: { content: pbUid } }] },
    "\u984C\u5EAB\u984C\u76EE": { relation: formal ? [{ id: p.problemPageId }] : [] },
    "\u6280\u80FD\u7BC0\u9EDE": { relation: formal ? p.skillPageIds.map((id) => ({ id })) : [] },
    "Problem ID": { rich_text: [{ text: { content: p.problemId } }] },
    "\u4F86\u6E90\u5E73\u53F0": { select: { name: p.source } },
    "\u4F5C\u7B54\u5E73\u53F0": { select: { name: p.judge } },
    "\u984C\u76EE\u9023\u7D50": { url: p.url },
    "\u96E3\u5EA6\uFF08D1\u2013D5\uFF09": { select: { name: p.difficulty } },
    "\u4F7F\u7528\u8A9E\u8A00": { multi_select: [{ name: "C++" }] },
    "\u6700\u65B0\u63D0\u4EA4\u7D50\u679C": { select: { name: result } },
    "Assistance": { select: { name: assistance } },
    "\u7368\u7ACB\u5B8C\u6210": { checkbox: independent },
    "\u5617\u8A66\u6B21\u6578": { number: attempts },
    "\u89E3\u984C\u6642\u9593(\u5206\u9418)": { number: timeMin },
    "\u5B78\u7FD2\u968E\u6BB5": { select: { name: stage } },
    "\u932F\u8AA4\u985E\u578B": { multi_select: errors.map((name) => ({ name })) },
    "\u6838\u5FC3\u6536\u7A6B": { rich_text: takeaway ? [{ text: { content: takeaway } }] : [] },
    "Writeback ID": { rich_text: [{ text: { content: writebackId } }] },
    "\u7D00\u9304\u4F86\u6E90": { select: { name: "HTML Direct" } },
    "\u7D00\u9304\u6027\u8CEA": { select: { name: recordKind } },
    "\u5B78\u7FD2\u6B77\u7A0B\u5019\u9078": { checkbox: false }
  };
  const page = await notionFetch(env, "/pages", {
    method: "POST",
    body: JSON.stringify({
      parent: { type: "data_source_id", data_source_id: REC_DS },
      icon: { type: "emoji", emoji: recordKind === "\u6B63\u5F0F\u7D00\u9304" ? "\u{1F9E9}" : "\u{1F9EA}" },
      properties,
      children: makePageBody(p, { result, assistance, independent, attempts, timeMin, stage, errors, takeaway, reviewDate })
    })
  });
  return {
    duplicate: false,
    page_id: page.id,
    url: page.url,
    writeback_id: writebackId,
    rec_uid: formatRecUid(page),
    record_title: p.displayTitle
  };
}
__name(writeRecord, "writeRecord");
var index_default = {
  async fetch(request, env) {
    const url = new URL(request.url);
    if ((request.method === "GET" || request.method === "HEAD") && url.pathname.startsWith("/learn/") && url.pathname.length > 1 && url.pathname.endsWith("/")) {
      const canonical = new URL(request.url);
      canonical.pathname = canonical.pathname.replace(/\/+$/, "");
      return Response.redirect(canonical.toString(), 308);
    }
    if ((request.method === "GET" || request.method === "HEAD") && (url.pathname === "/workspace-v5-5" || url.pathname === "/workspace-v5-5.html")) {
      const target = legacyV55Redirect(url);
      if (target) return Response.redirect(target.toString(), 308);
      console.warn(JSON.stringify({
        event: "legacy_route_unmapped_pb",
        route: url.pathname,
        pb: url.searchParams.get("pb")
      }));
      return env.ASSETS.fetch(request);
    }
    if ((request.method === "GET" || request.method === "HEAD") && url.pathname === "/tools/custom-oj.html") {
      return new Response(request.method === "HEAD" ? null : "Not Found", { status: 404, headers: { "Cache-Control": "no-store" } });
    }
    if ((request.method === "GET" || request.method === "HEAD") && (url.pathname === "/oj" || url.pathname === "/tools/custom-oj" || /^\/oj\/problem\/PB-\d+$/i.test(url.pathname))) {
      return serveAsset(env, request, "/_internal/custom-oj.html", { "X-APCS-Tool": "custom-oj" });
    }
    if ((request.method === "GET" || request.method === "HEAD") && url.pathname === "/learn/psv/math-correctness/lab/psv04-correctness-boundary") {
      const target = new URL(request.url);
      target.pathname = "/learn/psv/math-correctness/lab/psv04-correctness-claim-board";
      return Response.redirect(target.toString(), 308);
    }
    if (request.method === "GET" || request.method === "HEAD") {
      if (/^\/visuals\/skill\/[^/]+$/i.test(url.pathname)) {
        return serveAsset(env, request, "/visuals/skill/shell.html", { "X-APCS-Visual": "skill-detail" });
      }
      if (/^\/visuals\/unit\/[^/]+$/i.test(url.pathname)) {
        return serveAsset(env, request, "/visuals/unit/shell.html", { "X-APCS-Visual": "unit-roadmap" });
      }
      const semantic = resolveSemanticPath(url.pathname);
      if (semantic?.kind === "lesson") return serveSemanticLesson(env, request, semantic.lesson, url);
      if (semantic?.kind === "lab") return serveSemanticLab(env, request, semantic.lesson, semantic.labSlug);
      if (semantic?.kind === "invalid") return htmlError("\u627E\u4E0D\u5230\u5B78\u7FD2\u8DEF\u5F91", `ROUTE-v1: ${semantic.reason}`, 404);
      if (url.pathname.startsWith("/_internal/")) return htmlError("Not Found", "Internal learning assets are not public learner routes.", 404);
    }
    if (request.method === "GET" && url.pathname.startsWith("/api/visuals/")) {
      if (!env.NOTION_API_TOKEN || !env.WRITE_KEY) {
        return json({ ok: false, error: "SERVER_NOT_CONFIGURED" }, 503);
      }
      if (!await visualReadAuthorized(request, env)) {
        return json({ ok: false, error: "UNAUTHORIZED" }, 401);
      }
      try {
        if (url.pathname === "/api/visuals/dashboard") {
          return json(await buildVisualDashboard(env));
        }
        if (url.pathname === "/api/visuals/problem-ladder") {
          const result = await buildProblemLadder(env, url.searchParams.get("lesson") || "");
          if (!result.ok) return json({ ok: false, error: result.error }, result.status);
          return json(result);
        }
        if (url.pathname === "/api/visuals/system-audit") {
          const result = await buildSystemIntegrityAudit(env);
          return json(result, result.ok ? 200 : 409);
        }
        return json({ ok: false, error: "VISUAL_API_NOT_FOUND" }, 404);
      } catch (err) {
        console.error(JSON.stringify({
          event: "visual_read_failed",
          path: url.pathname,
          message: err instanceof Error ? err.message : String(err)
        }));
        return json({ ok: false, error: "NOTION_READ_FAILED" }, 502);
      }
    }
    if (request.method === "GET" && url.pathname === "/api/health") {
      return json({ ok: true, service: "apcs-rec-writeback", schema: "REC-v3.1", evidence_schema: "EV-v1", remote_writeback_schema: REMOTE_WRITEBACK_SCHEMA, route_schema: "ROUTE-v1", visual_schema: "VIS-v1-full", notion_version: NOTION_VERSION });
    }
    const legacyRootPost = request.method === "POST" && url.pathname === "/";
    const recordPost = request.method === "POST" && url.pathname === "/api/record";
    if (!legacyRootPost && !recordPost) return json({ ok: false, error: "METHOD_NOT_ALLOWED" }, 405);
    if (!env.NOTION_API_TOKEN || !env.WRITE_KEY) {
      return json({ ok: false, error: "SERVER_NOT_CONFIGURED" }, 503);
    }
    const contentLength = Number(request.headers.get("Content-Length") || "0");
    if (contentLength > MAX_BODY_BYTES) return json({ ok: false, error: "PAYLOAD_TOO_LARGE" }, 413);
    let body;
    try {
      const raw = await request.text();
      if (new TextEncoder().encode(raw).byteLength > MAX_BODY_BYTES) {
        return json({ ok: false, error: "PAYLOAD_TOO_LARGE" }, 413);
      }
      body = JSON.parse(raw);
    } catch {
      return json({ ok: false, error: "INVALID_JSON" }, 400);
    }
    const suppliedKey = request.headers.get("X-APCS-Write-Key") || cleanText(body.write_key, 256);
    if (!await secureEqual(suppliedKey, env.WRITE_KEY)) {
      return json({ ok: false, error: "UNAUTHORIZED" }, 401);
    }
    try {
      if (body?.schema_version === REMOTE_WRITEBACK_SCHEMA) {
        const result = await writeRemoteBundle(env, body, new URL(request.url).origin);
        if ("error" in result) return json({ ok: false, error: result.error }, result.status);
        console.log(JSON.stringify({
          event: "v23_remote_writeback",
          writeback_id: result.writeback_id,
          rec_duplicate: result.rec.duplicate,
          evidence_count: result.evidence.length,
          evidence_duplicates: result.evidence.filter((item) => item.duplicate).length
        }));
        return json({ ok: true, ...result }, result.created ? 201 : 200);
      }
      const result = await writeRecord(env, body, new URL(request.url).origin);
      if ("error" in result) return json({ ok: false, error: result.error }, result.status);
      console.log(JSON.stringify({
        event: "rec_write",
        duplicate: result.duplicate,
        writeback_id: result.writeback_id,
        rec_uid: result.rec_uid
      }));
      return json({ ok: true, ...result }, result.duplicate ? 200 : 201);
    } catch (err) {
      console.error(JSON.stringify({
        event: "rec_write_failed",
        message: err instanceof Error ? err.message : String(err)
      }));
      return json({ ok: false, error: "NOTION_WRITE_FAILED" }, 502);
    }
  }
};
export {
  index_default as default
};
//# sourceMappingURL=index.js.map
