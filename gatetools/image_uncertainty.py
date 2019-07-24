"""

This module provides a function to compute relative statistical
uncertainty (typically for Edep or Dose), with the history by history
method as explained for example in [Chetty2006]

"""

# -----------------------------------------------------------------------------
#   Copyright (C): OpenGATE Collaboration
#   This software is distributed under the terms
#   of the GNU Lesser General  Public Licence (LGPL)
#   See LICENSE.md for further details
# -----------------------------------------------------------------------------


import itk
import gatetools as gt
from functools import reduce
import operator
import numpy as np

def relative_uncertainty_Poisson(x, threshold=0):
    sigma = np.sqrt(x)
    u = np.divide(sigma, x, out=np.ones_like(x), where=x > threshold)
    return u


def relative_uncertainty(x, sq_x, N, threshold=0):
    u = np.sqrt( (N*sq_x - x*x) / (N-1) )
    u = np.divide(u, x, out=np.ones_like(x), where=x > threshold)
    return u

def relative_uncertainty_by_slice(x, threshold=0, sq_x=[], N=0):
    i=0
    means = []
    nb = []
    uncertainty = np.copy(x)
    uncertainty.fill(0.0)
    use_square = False
    if len(sq_x)>0:
        use_square = True
    else:
        sq_x = x
    for s,sq in zip(x, sq_x):
        t = np.max(s)*threshold
        sigma = np.sqrt(s)
        if use_square:
            u = relative_uncertainty(s, sq, N, t)
        else:
            u = relative_uncertainty_Poisson(s, t)
        n = len(np.where(s > t)[0])
        if n==0:
            mean = 1.0
        else:
            mean = u[np.where(s > t)].sum()
            mean = mean/n
        means.append(mean)
        nb.append(n)
        uncertainty[i] = u
        i = i + 1
    return uncertainty, means, nb

def check_N(N):
    N = float(N)
    if N<0:
        raise RuntimeError('ERROR: N  must be positive')


def image_uncertainty(img_list=[], img_squared_list=[], N=0, threshold=0):
    check_N(N)

    # Get the sums
    img_sum = gt.image_sum(img_list)
    img_sq_sum = gt.image_sum(img_squared_list)

    # View as np
    np_sum = itk.GetArrayViewFromImage(img_sum)
    np_sq_sum = itk.GetArrayViewFromImage(img_sq_sum)

    # Compute relative uncertainty [Chetty 2006]
    t = np.max(np_sum)*threshold
    uncertainty = relative_uncertainty(np_sum, np_sq_sum, N, t)

    # create and return itk image
    img_uncertainty = itk.GetImageFromArray(uncertainty)
    img_uncertainty.CopyInformation(img_sum)
    return img_uncertainty


def image_uncertainty_by_slice(img_list=[], img_squared_list=[], N=0, threshold=0):
    check_N(N)

    # Get the sums
    img_sum = gt.image_sum(img_list)
    img_sq_sum = gt.image_sum(img_squared_list)

    # View as np
    np_sum = itk.GetArrayViewFromImage(img_sum)
    np_sq_sum = itk.GetArrayViewFromImage(img_sq_sum)

    # compute uncertainty
    uncertainty, means, nb = relative_uncertainty_by_slice(np_sum, threshold, np_sq_sum, N)

    # create and return itk image
    img_uncertainty = itk.GetImageFromArray(uncertainty)
    img_uncertainty.CopyInformation(img_sum)
    return img_uncertainty, means, nb


def image_uncertainty_Poisson(img_list=[], threshold=0):
    # Get the sums
    img_sum = gt.image_sum(img_list)

    # View as np
    np_sum = itk.GetArrayViewFromImage(img_sum)

    # Convert to float
    np_sum = np_sum.astype(np.float64)

    # Get stddev (variance is the mean)
    sigma = np.sqrt(np_sum)

    # compute uncertainty
    t = np.max(np_sum)*threshold
    uncertainty = relative_uncertainty_Poisson(np_sum, t)

    # np is double, convert to float32
    uncertainty = uncertainty.astype(np.float32)

    # create and return itk image
    img_uncertainty = itk.GetImageFromArray(uncertainty)
    img_uncertainty.CopyInformation(img_sum)
    return img_uncertainty


def image_uncertainty_Poisson_by_slice(img_list=[], threshold=0):
    # Get the sums
    img_sum = gt.image_sum(img_list)

    # View as np
    np_sum = itk.GetArrayViewFromImage(img_sum)

    # Convert to float
    np_sum = np_sum.astype(np.float64)

    # compute uncertainty
    uncertainty, means, nb = relative_uncertainty_by_slice(np_sum, threshold)

    # np is double, convert to float32
    uncertainty = uncertainty.astype(np.float32)

    # create and return itk image
    img_uncertainty = itk.GetImageFromArray(uncertainty)
    img_uncertainty.CopyInformation(img_sum)
    return img_uncertainty, means, nb
