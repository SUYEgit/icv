# -*- coding: UTF-8 -*-
from icv.utils.itis import is_seq
from .bbox import BBox

class BBoxList(object):
    def __init__(self,bbox_list):
        assert is_seq(bbox_list) or isinstance(bbox_list,BBoxList),"param bbox_list should be type of sequence or BBoxList"
        if isinstance(bbox_list,BBoxList):
            bbox_list = bbox_list.bbox_list
        bbox_list = list(bbox_list)

        for bbox_item in bbox_list:
            assert isinstance(bbox_item,BBox),"bbox should be type of BBox"

        self._labels = None
        self._bbox_list = bbox_list

    def __len__(self):
        return len(self.bbox_list)

    def __getitem__(self, item):
        assert item < self.length, "index out of the range."
        bbox = self.bbox_list[item]
        return bbox

    def tolist(self):
        return [[bbox.xmin,bbox.ymin,bbox.xmax,bbox.ymax] for bbox in self._bbox_list]

    @property
    def bbox_list(self):
        return self._bbox_list

    @property
    def length(self):
        return len(self)

    @property
    def labels(self):
        if self._labels:
            return self._labels

        self._labels = []
        for bbox in self.bbox_list:
            self._labels.append(bbox.lable)
        return self._labels

    @property
    def is_empty(self):
        return self.length == 0

    @property
    def xmin(self):
        return min([bbox.xmin for bbox in self.bbox_list])

    @property
    def ymin(self):
        return min([bbox.ymin for bbox in self.bbox_list])

    @property
    def xmax(self):
        return max([bbox.xmax for bbox in self.bbox_list])

    @property
    def ymax(self):
        return max([bbox.ymax for bbox in self.bbox_list])

