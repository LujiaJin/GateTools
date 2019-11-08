"""

This module provides a function to crop image

"""

# -----------------------------------------------------------------------------
#   Copyright (C): OpenGATE Collaboration
#   This software is distributed under the terms
#   of the GNU Lesser General  Public Licence (LGPL)
#   See LICENSE.md for further details
# -----------------------------------------------------------------------------


import itk
import gatetools as gt
import numpy as np

def image_crop(img, bg=0):
    """
    Crop an image according to a background value
    """

    # Img image type
    bg = int(bg)
    ImageType = type(img)
    Dim = 3
    dims = np.array(img.GetLargestPossibleRegion().GetSize())
    if len(dims) != 3:
        print('ERROR: only 3D image supported')
        exit(0)

    # Cast to an image type which is compatible (ushort)
    OutputPixelType = itk.ctype('unsigned short')
    OutputImageType = itk.Image[OutputPixelType, Dim]
    caster = itk.CastImageFilter[ImageType, OutputImageType].New()
    caster.SetInput(img)
    caster.Update()
    img = caster.GetOutput()
    TempImageType = type(img)

    # create filters for crop
    LabelType = itk.ctype('unsigned long')
    LabelObjectType = itk.StatisticsLabelObject[LabelType, Dim]
    LabelMapType = itk.LabelMap[LabelObjectType]
    # print(itk.LabelImageToLabelMapFilter.GetTypes())
    converter = itk.LabelImageToLabelMapFilter[TempImageType, LabelMapType].New()
    converter.SetBackgroundValue(bg);
    converter.SetInput(img);
    autocrop = itk.AutoCropLabelMapFilter[LabelMapType].New()
    autocrop.SetInput(converter.GetOutput())
    remap = itk.LabelMapToLabelImageFilter[LabelMapType, TempImageType].New()
    remap.SetInput(autocrop.GetOutput())

    # recast to initial type
    endcaster = itk.CastImageFilter[TempImageType, ImageType].New()
    endcaster.SetInput(remap.GetOutput())

    # Go !
    endcaster.Update()
    output = endcaster.GetOutput()
    return output

def image_crop_with_bb(img, bb):
    """
    Crop an image according to a bounding box (see "bounding_box" module).
    """
    dims = np.array(img.GetLargestPossibleRegion().GetSize())
    if len(dims) != 3:
        print('ERROR: only 3D image supported')
        exit(0)
    #inclusive
    from_index = np.maximum(np.zero(3,dtype=int),np.array(img.TransformPhysicalPointToIndex(bb.mincorner)))
    #exclusive
    to_index = np.minimum(dims,np.array(img.TransformPhysicalPointToIndex(bb.maxcorner))+1)
    cropper = itk.RegionOfInterestImageFilter.New(Input=input_img)
    region = cropper.GetRegionOfInterest()
    indx=region.GetIndex()
    size=region.GetSize()
    for j in range(3):
        indx.SetElement(j,int(from_index[j]))
        size.SetElement(j,int(to_index[j]-from_index[j]))
    region.SetIndex(indx)
    region.SetSize(size)
    cropper.SetRegionOfInterest(region)
    cropper.Update()
    return cropper.GetOutput()

