Mesh2HRTF-perf
==============

Performance fork of `Any2HRTF/Mesh2HRTF v1.3.0 <https://github.com/Any2HRTF/Mesh2HRTF/tree/v1.3.0>`_,
with sparse ILU setup, OpenMP matrix-vector multiplication and near assembly,
and parallel HRTF pressure postprocessing. The upstream **EUPL-1.2** license and
copyright notices are retained. Modifications are dated **2026-10-12**.

**Build (validated on Linux with GCC/OpenMP):**::

    make -C mesh2hrtf/NumCalc/src -j8

Set ``OMP_NUM_THREADS`` explicitly when running NumCalc. The default HRTF build
writes ``pEvalGrid``, ``pBoundary``, and ``vBoundary`` and omits ``vEvalGrid``.
Rebuild with ``EVALUATION_VELOCITY=1`` when evaluation velocity is required.

The accepted optimizations include parallel D/T assembly, parallel
postprocessing, and a coarsest-level matrix-vector layout. In three paired
eight-thread runs per frequency against the first performance release
(``9b386dc``), median wall time changed from 51.03 s to 44.00 s at 4 kHz and
from 915.66 s to 627.50 s at 24 kHz. Pressure and boundary output bytes were
identical. See `measurements, build options, and limitations
<docs/performance.md>`_ and the `reproducible checks
<tests/performance/README.md>`_. These timings use an already optimized release
as their baseline; they do not establish a whole-band speedup over upstream.

**Correctness against unmodified upstream:** A separate check on 2026-10-14
compared this repository's solver directly with Mesh2HRTF v1.3.0, commit
``e45d0436a6fbeca3db13828cbae23ca109225be3``, on Linux x86-64 with GCC 11.4.0.
The synthetic model had 2,048 triangles, asymmetric geometry, one driven face,
complex skin RLC admittance, and multiple evaluation distances. All nine
comparisons at 1, 4, and 12 kHz (one and eight threads, with an additional
eight-thread repeat) produced byte-identical ``pEvalGrid``, ``pBoundary``, and
``vBoundary`` files. Iteration counts and reported residuals also matched. The
checks exercised two FMM levels and both near- and far-field evaluation paths.
The `validation record and source hashes
<benchmarks/upstream-parity-2026-10-14.json>`_ identify the exact inputs and builds.
This is evidence for the tested inputs, not a proof for all meshes or frequencies.

**Platform scope:** In a separate macOS ARM64/GCC 15.2.0 check, the 1 kHz
single-thread case produced identical field files and the same 18 iterations,
but the reported residuals were ``1.32022e-10`` and ``1.32020e-10`` (an absolute
difference of approximately ``2e-15``). The strict residual check stopped that
run before the remaining cases. Cross-platform bit identity is not claimed.

The original Mesh2HRTF overview and references follow.

Mesh2HRTF
=========

.. image:: docs/figures/graphical_abstract-01.png
   :width: 800

`Mesh2HRTF <https://mesh2hrtf.org>`_ is an open-source software package for the numerical calculation of the head-related transfer functions (HRTFs). It targets researchers in the field of binaural audio. In a nutshell, Mesh2HRTF consists of three parts:

- Mesh2Input: preparation of the 3D head mesh and the acoustic parameters (source position, acoustic materials).
- NumCalc: wave-based numerical solver to calculate the sound pressure on the mesh and to project to the specified positions in the free field.
- Output2HRTFs: processing of the output from NumCalc to obtain HRTFs saved as SOFA files.

Mesh2HRTF is not an application - it is a toolbox aiming at researchers in the field of acoustics. Thus, before starting to use Mesh2HRTF, we assume the knowledge of the following background information:

- [1]_ and [2]_: General introductions to Mesh2HRTF as a whole.
- [3]_ and [4]_: Requirements on the mesh quality.
- [3]_: Information about the potential source and microphone models.
- [5]_ and [6]_: Introduction to mesh-grading strategies to reduce the RAM consumption and computation time.
- [7]_ and [8]_: Further background information on the wave-based numerical solver NumCalc used to calculate the HRTFs.

Documentation
=============

We recommend to go through the installation steps and the tutorials to get familiar with Mesh2HRTF before using it for your own projects. This will help you to understand the workflow and verify your first results.

Installation
    https://github.com/Any2HRTF/Mesh2HRTF/wiki/Installation

General Tutorials
    https://github.com/Any2HRTF/Mesh2HRTF/wiki/Tutorials

Complete Documentation
    https://github.com/Any2HRTF/Mesh2HRTF/wiki


Releases and Development
========================

This fork's ``master`` branch contains the performance changes described above
on top of Mesh2HRTF v1.3.0. Issues specific to these changes belong in
`this repository <https://github.com/SakuzyPeng/Mesh2HRTF-perf>`_.

Upstream Mesh2HRTF releases are available at https://github.com/Any2HRTF/Mesh2HRTF/releases.
Upstream development happens on its ``develop`` branch; if you would like to
contribute to Mesh2HRTF itself, please check `here <https://github.com/Any2HRTF/Mesh2HRTF/blob/develop/CONTRIBUTING.rst>`_.


References
==========

.. [1] F.\ Brinkmann, W. Kreuzer, J. Thomsen, S. Dombrovskis, K. PollackS. Weinzier, and P. Majdak, `''Recent Advances in an Open Software for Numerical HRTF Calculation,'' <https://doi.org/10.17743/jaes.2022.0078>`_, J. Audio Eng. Soc., vol. 71, no. 7/8, pp. 502-514, 2023, doi: 10.17743/jaes.2022.0078

.. [2] H\. Ziegelwanger, W. Kreuzer, and P. Majdak, `''Mesh2HRTF: An open-source software package for the numerical calculation of head-related transfer functions,'' <https://www.researchgate.net/publication/280007918_MESH2HRTF_AN_OPEN-SOURCE_SOFTWARE_PACKAGE_FOR_THE_NUMERICAL_CALCULATION_OF_HEAD-RELATED_TRANFER_FUNCTIONS>`_ Florence, Italy, Jul. 2015.

.. [3] H\. Ziegelwanger, P. Majdak, and W. Kreuzer, `''Numerical calculation of listener-specific head-related transfer functions and sound localization: Microphone model and mesh discretization,'' <https://doi.org/10.1121/1.4922518>`_ ,J. Acoust. Soc. Am., vol. 138, no. 1, pp. 208–222, Jul. 2015, doi: 10.1121/1.4922518.

.. [4] M\. Dinakaran, F. Brinkmann, S. Harder, R. Pelzer, P. Grosche, R. R. Paulsen, and S. Weinzierl, `''Perceptually motivated analysis of numerically simulated head-related transfer functions generated by various 3D surface scanning systems,'' <https://doi.org/10.1109/ICASSP.2018.8461789>`_ in IEEE Int. Conf. Acoustics, Speech and Signal Processing (ICASSP), Calgary, Canada, Apr. 2018, pp. 551–555. doi: 10.1109/ICASSP.2018.8461789.

.. [5] T\. Palm, S. Koch, F. Brinkmann, and M. Alexa, `''Curvature-adaptive mesh grading for numerical approximation of head-related transfer functions,'' <https://www.researchgate.net/publication/356264260_Curvature-adaptive_mesh_grading_for_numerical_approximation_of_head-related_transfer_functions>`_ in Fortschritte der Akustik – DAGA 2021, Vienna, Austria, Aug. 2021, pp. 1111–1114.

.. [6] H\. Ziegelwanger, W. Kreuzer, and P. Majdak, `''A-priori mesh grading for the numerical calculation of the head-related transfer functions,'' <https://doi.org/10.1016/j.apacoust.2016.07.005>`_ Appl. Acoust., vol. 114, pp. 99–110, Dec. 2016, doi: 10.1016/j.apacoust.2016.07.005.

.. [7] W\. Kreuzer, K. Pollack, F. Brinkmann, and P. Majdak, `''NumCalc: An open-source BEM code for solving acoustic scattering problems,'' <https://doi.org/10.1016/j.enganabound.2024.01.008>`_, Engineering Analysis with Boundary Elements, vol. 161, pp. 157-178, April 2024.

.. [8] W\. Kreuzer, K. Pollack, P. Majdak, and F. Brinkmann, `''Mesh2HRTF / NumCalc: An Open-Source Project to Calculate HRTFs and wave scattering in 3D,'' <https://www.conforg.fr/erbnam2022/output_directory/data/articles/000042.pdf>`_ in Euroregio BNAM 2022, Aalborg, Denmark, May 2022.
