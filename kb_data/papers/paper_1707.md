# A fast and effective detection framework for whole-slide histopathology image analysis

**Authors:** Jun Ruan, Zhikui Zhu, Chenchen Wu, Guanglu Ye, Jingfan Zhou, Junqiu Yue, Gulistan Raja  
**Year:** 2021  
**Journal:** PLOS ONE  
**Volume:** 16  
**Issue:** 5  
**Pages:** e0251521  
**DOI:** 10.1371/journal.pone.0251521  

## Abstract
Pathologists generally pan, focus, zoom and scan tissue biopsies either under microscopes or on digital images for diagnosis. With the rapid development of whole-slide digital scanners for histopathology, computer-assisted digital pathology image analysis has attracted increasing clinical attention. Thus, the working style of pathologists is also beginning to change. Computer-assisted image analysis systems have been developed to help pathologists perform basic examinations. This paper presents a novel lightweight detection framework for automatic tumor detection in whole-slide histopathology images. We develop the Double Magnification Combination (DMC) classifier, which is a modified DenseNet-40 to make patch-level predictions with only 0.3 million parameters. To improve the detection performance of multiple instances, we propose an improved adaptive sampling method with superpixel segmentation and introduce a new heuristic factor, local sampling density, as the convergence condition of iterations. In postprocessing, we use a CNN model with 4 convolutional layers to regulate the patch-level predictions based on the predictions of adjacent sampling points and use linear interpolation to generate a tumor probability heatmap. The entire framework was trained and validated using the dataset from the Camelyon16 Grand Challenge and Hubei Cancer Hospital. In our experiments, the average AUC was 0.95 in the test set for pixel-level detection.

