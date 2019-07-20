# -*- coding: UTF-8 -*-
from .dataset import IcvDataSet
import os
import shutil
import cv2
import numpy as np
from icv.utils import load_voc_anno, make_empty_voc_anno, fcopy, list_from_file, list_to_file,is_file,is_dir
from icv.image import imread, imshow_bboxes
from .core.meta import SampleMeta, AnnoMeta
from .core.sample import Sample,Anno
from .core.bbox import BBox
from .core.bbox_list import BBoxList
from lxml.etree import Element, SubElement, ElementTree
import sys
import random
import copy

if sys.version_info[0] == 2:
    import xml.etree.cElementTree as ET
else:
    import xml.etree.ElementTree as ET


# TODO: 分割数据（图像目录、segment=1）
class Voc(IcvDataSet):
    def __init__(self, data_dir, split=None, use_difficult=True, keep_no_anno_image=True, mode="detect",
                 include_segment=True, categories=None, one_index=False, image_suffix="jpg"):
        self.root = data_dir
        self.split = split if split else "trainval"
        self.mode = mode
        self.is_seg_mode = self.mode != "detect"
        self.include_segment = include_segment
        self.image_set = "Main" if self.mode == "detect" else "Segmentation"

        self.use_difficult = use_difficult
        self.keep_no_anno_image = keep_no_anno_image
        self.image_suffix = image_suffix

        self._annopath = os.path.join(self.root, "Annotations", "%s.xml")
        self._imgpath = os.path.join(self.root, "JPEGImages", "%s." + image_suffix)
        self._seg_class_imgpath = os.path.join(self.root, "SegmentationClass", "%s.png")
        self._seg_object_imgpath = os.path.join(self.root, "SegmentationObject", "%s.png")
        self._imgsetpath = os.path.join(self.root, "ImageSets", self.image_set, "%s.txt")

        self.ids = list_from_file(self._imgsetpath % self.split)
        self.id2img = {k: v for k, v in enumerate(self.ids)}

        self.sample_db = {}
        if categories is not None:
            self.categories = categories
        else:
            self.categories = self.get_categories()
        super(Voc, self).__init__(self.ids, self.categories, self.keep_no_anno_image, one_index)

    def concat(self, voc, output_dir, reset=False, new_split=None):
        assert isinstance(voc, Voc)
        if new_split is None:
            if self.split == voc.split:
                new_split = self.split
            else:
                new_split = self.split + voc.split

        anno_path, image_path, imgset_path, imgset_seg_path, seg_class_image_path, seg_object_image_path = Voc.reset_dir(
            output_dir,reset=reset)

        ps0 = fcopy([self._imgpath % id for id in self.ids], image_path)
        ps1 = fcopy([self._imgpath % id for id in voc.ids], image_path)

        ids0 = [os.path.basename(_).rsplit(".", 1)[0] for _ in ps0]
        ids1 = [os.path.basename(_).rsplit(".", 1)[0] for _ in ps1]

        fcopy([self._annopath % id for id in self.ids], anno_path)
        fcopy([voc._annopath % id for id in voc.ids], anno_path)

        if self.is_seg_mode:
            fcopy([self._seg_class_imgpath % id for id in self.ids], seg_class_image_path)
            fcopy([self._seg_object_imgpath % id for id in self.ids], seg_object_image_path)

        if voc.is_seg_mode:
            fcopy([voc._seg_class_imgpath % id for id in voc.ids], seg_class_image_path)
            fcopy([voc._seg_object_imgpath % id for id in voc.ids], seg_object_image_path)

        if self.mode == voc.mode:
            ids = ids0 + ids1
            setpath = imgset_seg_path if self.is_seg_mode else imgset_path

            list_to_file(ids, os.path.join(setpath, "%s.txt" % new_split))
        else:
            if not self.is_seg_mode:
                list_to_file(ids0, os.path.join(imgset_path, "%s.txt" % new_split))
            else:
                list_to_file(ids0, os.path.join(imgset_seg_path, "%s.txt" % new_split))

            if not voc.is_seg_mode:
                list_to_file(ids1, os.path.join(imgset_path, "%s.txt" % new_split))
            else:
                list_to_file(ids1, os.path.join(imgset_seg_path, "%s.txt" % new_split))

        return Voc(
            output_dir,
            split=new_split,
            use_difficult=self.use_difficult,
            keep_no_anno_image=self.keep_no_anno_image,
            mode=self.mode,
            include_segment=self.include_segment,
            one_index=self.one_index,
            categories=self.categories + voc.categories,
            image_suffix=self.image_suffix
        )

    def sub(self, count=0, ratio=0, shuffle=True, output_dir=None):
        voc = super(Voc, self).sub(count,ratio,shuffle,output_dir)
        voc.root = output_dir

    def save(self, output_dir, split=None):
        split = split if split is not None else self.split
        anno_path, image_path, imgset_path, imgset_seg_path, seg_class_image_path, seg_object_image_path = Voc.reset_dir(
            output_dir)
        for id in self.ids:
            fcopy(self._annopath % id, anno_path)
            fcopy(self._imgpath % id, image_path)
            fcopy(self._seg_class_imgpath % id, seg_class_image_path)
            fcopy(self._seg_object_imgpath % id, seg_object_image_path)

        if self.is_seg_mode:
            list_to_file(self.ids, os.path.join(imgset_seg_path, "%s.txt" % split))
        else:
            list_to_file(self.ids, os.path.join(imgset_path, "%s.txt" % split))

    @staticmethod
    def reset_dir(dist_dir,reset=False):
        if not reset:
            assert is_dir(dist_dir)
        if reset and os.path.exists(dist_dir):
            shutil.rmtree(dist_dir)

        anno_path = os.path.join(dist_dir, "Annotations")
        image_path = os.path.join(dist_dir, "JPEGImages")
        imgset_path = os.path.join(dist_dir, "ImageSets", "Main")

        imgset_seg_path = os.path.join(dist_dir, "ImageSets", "Segmentation")
        seg_class_image_path = os.path.join(dist_dir, "SegmentationClass")
        seg_object_image_path = os.path.join(dist_dir, "SegmentationObject")

        for _path in [anno_path,image_path,imgset_path,imgset_seg_path,seg_class_image_path,seg_object_image_path]:
            if reset or not is_dir(_path):
                os.makedirs(_path)

        return anno_path, image_path, imgset_path, imgset_seg_path, seg_class_image_path, seg_object_image_path

    def get_categories(self):
        self.get_samples()
        categories = []
        for anno_sample in self.samples:
            label_list = anno_sample.bbox_list.labels
            if label_list:
                categories.extend(label_list)
        categories = list(set(categories))
        categories.sort()
        return categories

    def get_sample(self, id):
        if id in self.sample_db:
            return self.sample_db[id]

        anno_file = self._annopath % id
        image_file = self._imgpath % id

        if not is_file(image_file):
            raise FileNotFoundError("image file : {} not exist!".format(image_file))

        if not is_file(anno_file):
            anno_data = make_empty_voc_anno()
        else:
            anno_data = load_voc_anno(anno_file)["annotation"]

        sample_meta = SampleMeta({
            k:anno_data[k]
            for k in anno_data if k not in ["object"]
        })

        segcls_file = self._seg_class_imgpath % id
        segobj_file = self._seg_object_imgpath % id

        annos = []
        if "object" in anno_data:
            for obj in anno_data["object"]:
                if "difficult" in obj and obj["difficult"] != '0' and self.use_difficult:
                    continue
                label = obj["name"]
                anno = Anno(
                    bbox=BBox(
                        xmin=int(obj["bndbox"]["xmin"]),
                        ymin=int(obj["bndbox"]["ymin"]),
                        xmax=int(obj["bndbox"]["xmax"]),
                        ymax=int(obj["bndbox"]["ymax"]),
                        label=label,
                    ),
                    label=label,
                    meta=AnnoMeta({
                        k:obj["k"]
                        for k in obj if k not in ["name","bndbox"]
                    })
                )

                if is_file(segcls_file):
                    pass

                annos.append(anno)

        sample = Sample(
            id,
            image_file,
            annos,
            sample_meta
        )

        self.sample_db[id] = sample
        return sample

        #
        #
        #
        # # TODO wait for delete
        # anno_data["size"]["width"] = image_width
        # anno_data["size"]["height"] = image_height
        # anno_data["size"]["depth"] = image_depth
        #
        # anno_sample = Sample.init(
        #     name=os.path.basename(image_file).rsplit(".", 1)[0],
        #     bbox_list=BBoxList(
        #         bbox_list=[
        #             BBox(
        #                 xmin=int(object["bndbox"]["xmin"]),
        #                 ymin=int(object["bndbox"]["ymin"]),
        #                 xmax=int(object["bndbox"]["xmax"]),
        #                 ymax=int(object["bndbox"]["ymax"]),
        #                 label=object["name"],
        #                 **anno_data
        #             )
        #             for object in anno_data["object"]
        #             if "difficult" not in object or object["difficult"] == '0' or (
        #                         object["difficult"] != '0' and self.use_difficult)
        #         ]
        #     ),
        #     image=image_file,
        #     **anno_data
        # )
        #
        # self.sample_db[id] = sample
        # return anno_sample

    def _write_sample(self, anno_sample, dist_path):
        assert "folder" in anno_sample
        assert "filename" in anno_sample
        assert "size" in anno_sample
        assert "width" in anno_sample["size"]
        assert "height" in anno_sample["size"]
        assert "depth" in anno_sample["size"]
        assert "object" in anno_sample

        segmented = anno_sample["segmented"] if self.include_segment and "segmented" in anno_sample else "0"
        pose = "Unspecified"

        root = Element("annotation")
        SubElement(root, 'folder').text = anno_sample["folder"]
        SubElement(root, 'filename').text = anno_sample["filename"]

        source = SubElement(root, 'source')
        SubElement(source, 'database').text = "The VOC2012 Database"
        SubElement(source, 'annotation').text = "PASCAL VOC2012"
        SubElement(source, 'image').text = "flickr"

        size = SubElement(root, 'size')
        SubElement(size, 'width').text = str(anno_sample["size"]["width"])
        SubElement(size, 'height').text = str(anno_sample["size"]["height"])
        SubElement(size, 'depth').text = str(anno_sample["size"]["depth"])

        SubElement(root, 'segmented').text = segmented

        for object in anno_sample["object"]:
            obj = SubElement(root, 'object')
            SubElement(obj, 'name').text = object["name"]
            SubElement(obj, 'pose').text = pose
            truncated = str(object["truncated"]) if "truncated" in object else "0"
            difficult = str(object["difficult"]) if "difficult" in object else "0"
            if difficult == "1" and not self.use_difficult:
                continue
            SubElement(obj, 'truncated').text = truncated
            SubElement(obj, 'difficult').text = difficult
            bndbox = SubElement(obj, 'bndbox')
            SubElement(bndbox, 'xmin').text = str(object["bndbox"]["xmin"])
            SubElement(bndbox, 'ymin').text = str(object["bndbox"]["ymin"])
            SubElement(bndbox, 'xmax').text = str(object["bndbox"]["xmax"])
            SubElement(bndbox, 'ymax').text = str(object["bndbox"]["ymax"])

        tree = ElementTree(root)
        tree.write(dist_path, encoding='utf-8', pretty_print=True)

    def _get_mask_np(self, mask_image_path, bboxes):
        """
        根据mask png分割图片返回mask数组
        :param mask_image_path: 分割的mask png图片文件路径
        :param bbox: 分割框列表
        :return:
        """
        seg_image_mask = cv2.imread(mask_image_path, 0)
        maskes = []
        for bbox in bboxes:
            mask = np.copy(seg_image_mask)
            xmin, ymin, xmax, ymax = bbox[0], bbox[1], bbox[2], bbox[3]
            global_idx = np.array(np.where(mask != 0))
            inbox_idx = global_idx[:, np.where(
                (global_idx[0, :] >= ymin) & (global_idx[0, :] <= ymax) & (global_idx[1, :] >= xmin) & (
                            global_idx[1, :] <= xmax))[0]]
            mask[inbox_idx[0], inbox_idx[1]] = 256
            mask[(mask != 256) & (mask != 0)] = 0
            mask[inbox_idx[0], inbox_idx[1]] = 1
            maskes.append(mask)

        return np.array(maskes)

    def _cover_with_maskpng(self, sample, with_segobj=False):
        assert isinstance(sample, Sample)
        image = imread(sample.image)

        if with_segobj:
            seg_image_mask = cv2.imread(self._seg_object_imgpath % sample.name, 0)
        else:
            seg_image_mask = cv2.imread(self._seg_class_imgpath % sample.name, 0)

        if seg_image_mask is None:
            return image

        binset = list(set(seg_image_mask.flatten().tolist()))
        for bin in binset:
            color_mask = self.color_map[self.id2cat[bin % self.num_classes]]
            color_mask = np.array(color_mask)
            if bin == 0:
                continue
            mask = np.zeros_like(seg_image_mask, dtype=np.uint8)
            mask[seg_image_mask == bin] = 1
            mask_bin = mask.astype(np.bool)
            image[mask_bin] = image[mask_bin] * 0.5 + color_mask * 0.5

        return image

    def vis(self, id=None, is_show=False, output_path=None, seg_inbox=True):
        samples = []
        if id:
            sample = self.get_sample(id)
            samples.append(sample)
        else:
            samples = self.get_samples()

        print(self.ids)

        image_vis = []
        for sample in samples:
            mask_np = None

            image = sample.image
            if sample.fields.segmented == "1":
                if seg_inbox:
                    mask_image_path = self._seg_object_imgpath % sample.name
                    mask_np = self._get_mask_np(mask_image_path, sample.bbox_list.tolist())
                    mask_np.astype(np.uint8)
                    mask_np[mask_np != 0] = 1
                else:
                    image = self._cover_with_maskpng(sample, with_segobj=True)

            save_path = (output_path if id else os.path.join(output_path,sample.fields.filename)) if output_path else None

            image_drawed = imshow_bboxes(image, sample.bbox_list, sample.bbox_list.labels, classes=self.categories,
                                         masks=mask_np, is_show=is_show, save_path=save_path)
            image_vis.append(image_drawed)

        return image_vis[0] if id else image_vis
