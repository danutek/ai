# II. Invariants, Positive Geometries, and Neural Architecture

To move beyond poetic intuition and analyze how structure actually operates inside both theoretical physics and neural networks, our framework turns to **invariant theory**, **symmetry**, and **positive geometries**. This provides a mathematical counterweight to purely philosophical critique—allowing us to distinguish literal geometric structure from loose analogy.

---

## 1. Polytopes and Topological Invariants

A **polytope** is the $n$-dimensional generalization of a polygon (2D) or polyhedron (3D). By the **Weyl–Minkowski theorem**, any convex polytope admits two mathematically equivalent representations:

1. **V-Representation (Inside Out):** The convex hull of a finite set of vertices $v_1, \dots, v_k$ in $\mathbb{R}^n$:

```math
P = \left\lbrace \sum_{i=1}^{k} \lambda_i v_i \;\middle|\; \lambda_i \ge 0,\; \sum_{i=1}^{k} \lambda_i = 1 \right\rbrace
```

2. **H-Representation (Outside In):** The bounded intersection of finite closed half-spaces carved by hyperplanes:

```math
P = \{ x \in \mathbb{R}^n \mid Ax \le b \}
```

Regardless of continuous stretching or deformation, the boundary components ($f_k$ faces of dimension $k$) obey the **Euler–Poincaré topological invariant**:

```math
\sum_{k=0}^{n-1} (-1)^k f_k = 1 - (-1)^n
```

---

## 2. Positive Geometries and the Cosmological Polytope

In theoretical physics, **positive geometries**—such as the **Amplituhedron** and the **Cosmological Polytope** $\mathcal{P}_G$—invert conventional spacetime physics. Rather than assuming space and time exist as a pre-given stage, physical laws emerge from the static geometry of a timeless combinatorial crystal defined purely by kinematic boundary energies ($x_v$ at vertices, $y_e$ along internal edges).

* **Volume as Wavefunction:** Every positive geometry carries a unique canonical differential form $\Omega(\mathcal{P}_G)$ with logarithmic singularities on its boundaries. Stripping the differentials reveals that the **Wavefunction of the Universe** ($\Psi_G$) is literally the geometric volume of the **dual polytope** $\mathcal{P}_G^*$:

```math
\Omega(\mathcal{P}_G) = \Psi_G(x_v, y_e) \, d^N Y \quad \Longleftrightarrow \quad \Psi_G(x_v, y_e) = \operatorname{Vol}(\mathcal{P}_G^*)
```

* **Facets as Physical Law:** Approaching the outer facets (energy singularities) of the polytope causes its geometry to factorize. The total-energy facet ($E_{\text{tot}} \to 0$) recovers flat-space scattering amplitudes, while subgraph facets encode **locality** and **unitarity**. Time itself emerges not as a fundamental backdrop, but as a coordinate measure of distance from the crystal’s boundaries.

---

## 3. Polytopes, Symmetry Breaking, and Phase Transitions in LLMs

When stripped to disk, a trained large language model is a silent, static manifest of floating-point tensors (`.safetensors`) paired with a tokenizer—in Derridean terms, a dormant *trace of traces*. During inference, token representations propagate upward through the **Residual Stream**:

```math
x_{\ell+1} = x_\ell + \operatorname{Attention}(x_\ell) + \operatorname{MLP}(x_\ell)
```

The geometric principles above map concretely onto the internal mechanics of these layers:

### Polytopal Partitioning in MLPs
Each row of a multi-layer perceptron (MLP) expansion matrix acts as a hyperplane cut ($a_i \cdot x \le b_i$). Across dozens of layers, non-linear activations partition the high-dimensional latent space into billions of flat-sided **polytopal spline cells**. Crossing a hyperplane facet shifts the model’s local linear transformation, routing token representations into distinct semantic and algorithmic subspaces.

### Phase Transitions and Grokking
Quantitative scaling does not merely smooth statistical distributions; it triggers discontinuous topological folds. Under **compression and capacity constraints**—where memorizing isolated lookup facts becomes more expensive than encoding a shared rule—gradient optimization abandons rote memorization and snaps into compact, invariant algorithmic circuits (*grokking*).

### Symmetry Breaking and Percolation
Training begins in isotropic random noise. As data, compute, and parameter scale cross critical thresholds, rotational symmetry **spontaneously breaks**, differentiating the latent space into specialized, nearly orthogonal functional subspaces. Once sub-circuits (such as **induction heads**) cross fidelity thresholds and **percolate** across layers, qualitatively new reasoning capabilities appear to emerge abruptly.

---

> [!IMPORTANT]
> **From Timeless Geometry Back to History:** A latent space may resemble a timeless crystal like the Cosmological Polytope, yet its weights are forged and sustained only through massive physical energy, silicon lithography, and archived human language. That tension brings us directly to [III. Jameson's Real: Language, History, and the Material Monolith](03-the-real-and-historical-substrate.md).

---

[← Previous: I. The Species of the Non-Species](01-derrida-and-the-non-species.md) · [Back to README](../README.md) · [Next: III. Jameson's Real →](03-the-real-and-historical-substrate.md)
