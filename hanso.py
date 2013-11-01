"""
:Author: DOHMATOB Elvis Dopgima

"""

import numpy as np
import numpy.linalg
import time
from bfgs import bfgs
from postprocess import postprocess


def hanso(func, grad, sampgrad=False, normtol=1e-6, verbose=2,
          fvalquit=-np.inf, cpumax=np.inf, **kwargs):
    """
    HANSO: Hybrid Algorithm for Nonsmooth Optimization

    The algorithm is two-fold. Viz,
    BFGS phase: BFGS is run from multiple starting points, taken from
    the columns of x0 parameter, if provided, and otherwise 10 points
    generated randomly. If the termination test was satisfied at the
    best point found by BFGS, or if pars.nvar > 100, HANSO terminates;
    otherwise, it continues to:

    Gradient sampling phases: 3 gradient sampling phases are run from
    lowest point found, using sampling radii:
    10*options.evaldist, options.evaldist, options.evaldist/10
    Termination takes place immediately during any phase if
    options.cpumax CPU time is exceeded.

    References
    ----------
    A.S. Lewis and M.L. Overton, Nonsmooth Optimization via Quasi-Newton
    Methods, Math Programming, 2012

    J.V. Burke, A.S. Lewis and M.L. Overton, A Robust Gradient Sampling
    Algorithm for Nonsmooth, Nonconvex Optimization
    SIAM J. Optimization 15 (2005), pp. 751-779

    Parameters
    ----------
    func: callable function on 1D arrays of length nvar
        function being optimized

    grad: callable function
        gradient of func

    fvalquit: float, optional (default -inf)
        param passed to bfgs1run function

    normtol: float, optional (default 1e-4)
        termination tolerance for smallest vector in convex hull of saved
        gradients

    verbose: int, optional (default 1)
        param passed to bfgs1run function

    cpumax: float, optional (default inf)
        quit if cpu time in secs exceeds this (applies to total running time)

    sampgrad: boolean, optional (default False)
        if set, the gradient-sampling will be used to continue the algorithm
        in case the BFGS fails

    **kwargs: param-value dict
        optional parameters passed to bfgs backend. Possible key/values are:
        x0: 2D array of shape (nvar, nstart), optional (default None)
            intial points, one per column

        nvar: int, optional (default None)
            number of dimensions in the problem (exclusive x0)

        nstart: int, optional (default None)
            number of starting points for BFGS algorithm (exclusive x0)

        maxit: int, optional (default 100)
            param passed to bfgs1run function
        wolfe1: float, optional (default 0)
            param passed to bfgs1run function

        wolfe2: float, optional (default .5)
            param passed to bfgs1run function

    Returns
    -------
    x: D array of same length nvar = len(x0)
        final iterate

    _f: list of nstart floats
        final function values, one per run of bfgs1run

    _d: list of nstart 1D arrays, each of same length as input nvar
       final smallest vectors in convex hull of saved gradients,
       one array per run of bfgs1run

    _H: list of nstarts 2D arrays, each of shape (nvar, nvar)
       final inverse Hessian approximations, one array per run of bfgs1run

    itrecs: list of nstart int
       numbers of iterations, one per run of bfgs1run; see bfgs1run
       for details

    inforecs: list of int
        reason for termination; see bfgs1run for details

    Optional Outputs (in case output_records is True):
    Xrecs: list of nstart 2D arrays, each of shape (iter, nvar)
        iterates where saved gradients were evaluated; one array per run
        of bfgs1run; see bfgs1run
        for details

    Grecs: ist of nstart 2D arrays, each of shape (nvar, nvar)
        gradients evaluated at these points, one per run of bfgs1run;
        see bfgs1run for details

    wrecs: list of nstart 1D arrays, each of length iter
        weights defining convex combinations d = G*w; one array per
        run of bfgs1run; see bfgs1run for details

    fevalrecs: list of nstart 1D arrays, each of length iter
        records of all function evaluations in the line searches;
        one array per run of bfgs1run; see bfgs1run for details

    xrecs: list of nstart 2D arrays, each of length (iter, nvar)
        record of x iterates

    Hrecs: list of nstart 2D arrays, each of shape (iter, nvar)
       record of H (Hessian) iterates; one array per run of bfgs1run;
       see bfgs1run for details

    """

    def _log(msg, level=0):
        if verbose > level:
            print msg

    cpufinish = time.time() + cpumax

    # run BFGS step
    kwargs['output_records'] = 1
    x, f, d, H, it, info, X, G, w = bfgs(func, grad, fvalquit=fvalquit,
                                         normtol=normtol, cpumax=cpumax,
                                         verbose=verbose, **kwargs)

    # throw away all but the best result
    assert len(f) == np.array(x).shape[1], np.array(x).shape
    print f
    print x
    indx = np.argmin(f)
    f = f[indx]
    x = x[..., indx]
    d = d[..., indx]
    H = H[indx]  # bug if do this when only one start point: H already matrix
    X = X[indx]
    G = G[indx]
    w = w[indx]

    print f
    dnorm = numpy.linalg.norm(d, 2)
    # the 2nd argument will not be used since x == X(:,1) after bfgs
    loc, X, G, w = postprocess(x, np.nan, dnorm, X, G, w, verbose=verbose)

    if np.isnan(f) or np.isinf(f):
        _log('hanso: f is infinite or nan at all starting points')
        return x, f, loc, X, G, w, H

    if time.time() > cpufinish:
        _log('hanso: cpu time limit exceeded')
        _log('hanso: best point found has f = %g with local optimality '
             'measure: dnorm = %5.1e, evaldist = %5.1e' % (
                f, loc['dnorm'], loc['evaldist']))
        return x, f, loc, X, G, w, H

    if f < fvalquit:
        _log('hanso: reached target objective')
        _log('hanso: best point found has f = %g with local optimality'
             ' measure: dnorm = %5.1e, evaldist = %5.1e' % (
                f, loc['dnorm'], loc['evaldist']))
        return x, f, loc, X, G, w, H

    if dnorm < normtol:
        _log('hanso: verified optimality within tolerance in bfgs phase')
        _log('hanso: best point found has f = %g with local optimality '
             'measure: dnorm = %5.1e, evaldist = %5.1e' % (
                f, loc['dnorm'], loc['evaldist']))
        return x, f, loc, X, G, w, H
    elif not sampgrad:
        return x, f, loc, X, G, w, H
    else:
        # gradient-sampling stage: i'm to0 lazie to implement the
        # gradient-sampling right now ;)
        if sampgrad:
            raise NotImplementedError(
                'Gradient-Sampling trick not yet implemented!')

if __name__ == '__main__':
    func_names = [
        # 'Nesterov',
        # 'Rosenbrock "banana"',
        'l1-norm',
        # 'l2-norm'  # this is smooth and convex, we're only being ironic here
        ]
    wolfe_kinds = [0,  # weak
                   # 1 # strong
                   ]

    for func_name, j in zip(func_names, xrange(len(func_names))):
        nstart = 200
        nvar = 20
        if "l1-norm" in func_name:
            from example_functions import (l1 as func,
                                           gradl1 as grad)
        if "l2-norm" in func_name:
            from example_functions import (l2 as func,
                                           gradl2 as grad)
        elif "banana" in func_name:
            nvar = 2
            from example_functions import (rosenbrock_banana as func,
                                           grad_rosenbrock_banana as grad)
        elif "esterov" in func_name:
            from example_functions import (nesterov as func,
                                           grad_nesterov as grad)

        func_name = func_name + " in %i dimensions" % nvar
        print "Running HANSO for %s ..." % func_name

        import scipy.io
        x0 = scipy.io.loadmat("/tmp/x0.mat", squeeze_me=True,
                              struct_as_record=False)['x0']
        if x0.ndim == 1:
            x0 = x0.reshape((-1, 1), order='F')

        for strongwolfe in wolfe_kinds:

            # run BFGS
            x, f = hanso(func, grad,
                         x0=x0,
                         # nvar=nvar, nstart=nstart,
                         strongwolfe=strongwolfe,
                         maxit=1,
                         normtol=1e-6,
                         xnormquit=np.inf,
                         fvalquit=-np.inf,
                         cpumax=np.inf,
                         wolfe1=0.,
                         wolfe2=.5,
                         nvec=0,
                         scale=1,
                         evaldist=1e-6,
                         verbose=0
                         )[:2]
            print "xopt:", x
            print "fmin:", f

        print "... done (%s).\r\n" % func_name