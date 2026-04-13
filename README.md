
# MediBox-Lesion🩺

**TR:** Bounding Box Rehberli Mediastinal Lezyon Aday Maske Üretimi ve Görselleştirme Sistemi  
**EN:** Bounding Box Guided Mediastinal Lesion Proposal and Visualization System

---

# TR

## 1. Proje Özeti

MediBox-Lesion, 3D BT hacimleri üzerinde mediastinal lezyon analizi amacıyla geliştirilmiş bir medikal görüntü işleme projesidir.  
Bu proje, MELA veri setinde gerçek voxel seviyesinde segmentasyon maskesi bulunmaması nedeniyle, **bounding box rehberli aday maske üretimi ve görselleştirme** yaklaşımını benimsemektedir.

Sistem, final klinik segmentasyon modeli olarak değil; **lesion proposal / candidate mask generation** odaklı bir araştırma ve demo prototipi olarak konumlandırılmıştır.

---

## 2. Problem Tanımı

MELA veri seti aşağıdaki bilgileri içermektedir:

- 3D CT hacimleri (`.nii.gz`)
- 3D bounding box anotasyonları
- origin ve spacing bilgileri

Ancak veri setinde **gerçek segmentation ground truth maskesi bulunmamaktadır**.

Bu nedenle:

- klasik supervised segmentation eğitimi doğrudan uygulanamaz
- Dice, IoU gibi klasik segmentasyon metrikleri MELA üzerinde güvenilir biçimde hesaplanamaz

Bu problemi çözmek için projede **source-to-target transfer** yaklaşımı kullanılmıştır:

- Gerçek maskeli bir veri seti olan **NSCLC-Radiomics** üzerinde segmentasyon modeli eğitilmiştir
- Eğitilen model, **MELA** üzerinde bounding box rehberli inference için kullanılmıştır
- Sonuçlar final segmentasyon olarak değil, **aday lezyon maskesi** olarak değerlendirilmiştir

---

## 3. Projenin Temel Amaçları

Bu proje üç temel amaca sahiptir:

1. **MELA veri setindeki mediastinal lezyon bölgelerini görselleştirmek**
2. **Bounding box bilgisi ile model çıktısını karşılaştırmak**
3. **Canlı sunum ve analiz için interaktif bir demo arayüzü sağlamak**

---

## 4. Veri Setleri

### 4.1 MELA
Bu proje için **hedef veri setidir**.

İçerik:
- 3D CT hacimleri
- 3D bounding box anotasyonları
  - `coordX`, `coordY`, `coordZ`
  - `x_length`, `y_length`, `z_length`
- origin ve spacing bilgileri

Sınırlılıklar:
- gerçek segmentation maskesi yoktur
- Dice / IoU gibi metrikler doğrudan hesaplanamaz

### 4.2 NSCLC-Radiomics
Bu proje için **kaynak veri setidir**.

İçerik:
- thoracic CT hacimleri
- gerçek tümör segmentasyon maskeleri

Kullanım amacı:
- supervised model eğitimi
- nicel değerlendirme
- transfer learning için kaynak domain oluşturma

---

## 5. Proje Yaklaşımı

Proje iki ana aşamada geliştirilmiştir.

### 5.1 Aşama 1 — MELA üzerinde Heuristic Pseudo-Mask Yaklaşımı

İlk olarak bounding box içinden ROI çıkarılarak aşağıdaki yöntemlerle pseudo-mask üretimi denenmiştir:

- canonical orientation standardization
- annotation center transformation
- ROI extraction
- Gaussian smoothing
- center-guided seed selection
- intensity thresholding
- connected components
- morphology işlemleri
- fallback inner box yaklaşımı

Bu yöntem teknik olarak çalışsa da mediastinal bölgenin anatomik karmaşıklığı nedeniyle maske kalitesi tutarsız kalmıştır.

### 5.2 Aşama 2 — NSCLC’den MELA’ya Transfer Learning

İkinci aşamada **SimpleUNet** modeli, gerçek maskeli NSCLC veri setinde eğitilmiş ve daha sonra MELA üzerinde bbox-guided inference için kullanılmıştır.

Genel akış:
- NSCLC üzerinde model eğitimi
- MELA CT hacminin yüklenmesi
- bounding box ile ROI çıkarılması
- ROI normalizasyonu
- slice-based model inference
- post-processing
- tahminin tekrar full volume içine yerleştirilmesi
- görselleştirme

---

## 6. Temel Sonuçlar

### 6.1 MELA Batch Inference Sonuçları

Model, görüntü karşılığı bulunan geçerli MELA vakaları üzerinde uygulanmıştır.

Sonuçlar:
- **Geçerli vaka sayısı:** 372
- **Boş olmayan prediction:** 324
- **Boş prediction:** 48

Bu sonuç, modelin MELA üzerinde çoğu vakada boş olmayan bir aday bölge üretebildiğini göstermektedir.

Ancak prediction davranışı vaka bazında değişmektedir:
- **empty** → aday bölge üretilmemiş
- **small** → çok küçük aday bölge
- **medium** → orta büyüklükte aday bölge
- **large** → geniş / taşmış aday bölge

### 6.2 NSCLC Nicel Değerlendirme Sonuçları

NSCLC veri setinde gerçek maskeler bulunduğu için nicel metrikler burada hesaplanmıştır.

Validation sonuçları:
- **Ortalama Dice:** 0.2514
- **Ortalama IoU:** 0.1598
- **Ortalama Precision:** 0.1935
- **Ortalama Recall:** 0.5207

Yorum:
- model lezyon bölgesini kısmen yakalayabilmektedir
- recall değeri görece yüksektir
- precision düşüktür
- model yanlış pozitif üretmeye eğilimlidir
- final klinik segmentasyon için yeterli değildir

Bu sonuçlar, modelin MELA üzerinde final segmentasyon sistemi olarak değil, **candidate mask generator** olarak kullanılmasının daha doğru olduğunu desteklemektedir.

---

## 7. Sistem Özellikleri

### 7.1 MELA Demo Arayüzü

Streamlit arayüzü şu özellikleri içerir:

- manuel vaka seçimi
- example group seçimi (`empty`, `small`, `medium`, `large`)
- otomatik **best slice** seçimi
- bounding box görselleştirme
- ROI görselleştirme
- aday maske overlay gösterimi
- mask-visible slice inceleme
- previous / next case ile hızlı vaka geçişi

### 7.2 NSCLC Analiz Yapısı

NSCLC tarafında:
- model eğitimi
- validation metric hesaplama
- best / worst case analizi
- ground truth ve prediction karşılaştırması

sağlanmıştır.

---

## 8. Depo Yapısı

```text
MediBox-Lesion/
├── app/
│   └── streamlit_app.py
├── data/
│   ├── mela/
│   └── nsclc/
├── docs/
├── notebooks/
│   ├── mela/
│   └── nsclc/
├── results/
├── tests/
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt

---

## 9. Önemli Notebooklar

### MELA

- **`07_mela_single_case_model_inference.ipynb`**  
  Tek vaka inference

- **`08_mela_batch_model_inference.ipynb`**  
  Toplu inference

- **`09_mela_prediction_visualization.ipynb`**  
  Seçilen vakaların görsel analizi

### NSCLC

- **`03_train_simple_unet.ipynb`**  
  Model eğitimi

- **`06_nsclc_model_evaluation.ipynb`**  
  Dice / IoU / Precision / Recall değerlendirmesi

---

## 10. Kurulum

### 10.1 Depoyu klonlayın

```bash
git clone <repo-linki>
cd MediBox-Lesion

## 10. Kurulum

### 10.1 Depoyu klonlayın
```bash
git clone <repo-linki>
cd MediBox-Lesion

## 10.2 Sanal ortam oluşturun

python -m venv .venv

Windows için etkinleştirme:

```bash
.venv\Scripts\activate


## 10.3 Gerekli paketleri yükleyin

pip install -r requirements.txt


## 11. Veri Kurulumu

Büyük dosya boyutları nedeniyle medikal görüntüler, maskeler ve model ağırlıkları bu repoya dahil edilmemiştir.

Projeyi çalıştırmak için gerekli dosyaları aşağıdaki klasörlere manuel olarak yerleştirmeniz gerekir.

### 11.1 Gerekli MELA dosyaları

- `data/mela/annotations/mela_train_val_annotations.csv`
- `data/mela/annotations/mela_origin_spacing.csv`
- `data/mela/images/train/*.nii.gz`
- `data/mela/images/val/*.nii.gz`

### 11.2 Gerekli NSCLC dosyaları

- `data/nsclc/images/*.npy`
- `data/nsclc/masks/*.npy`
- `data/nsclc/models/best_model.pt`
- `data/nsclc/metadata/val_patients.csv`

### 11.3 Gerekli sonuç dosyaları

- `results/mela_batch_inference_summary.csv`
- `results/mela_selected_example_cases.csv`
- `results/mela_batch_predictions/*.npy`


## 12. Projeyi Çalıştırma

### 12.1 MELA demo arayüzünü başlatma

```bash
streamlit run app/streamlit_app.py

## 13. Dokümantasyon

Proje dokümanları `docs/` klasöründe yer almaktadır. Bu klasörde şunlar bulunur:

- Proje öneri dokümanı
- Mimari dokümanı
- Teknoloji yığını dokümanı
- Kurulum kılavuzu
- API / modül dokümantasyonu
- Kullanıcı kılavuzu
- Geliştirici kılavuzu
- Test raporu
- Final raporu
- Haftalık raporlar

## 14. Projenin Konumlandırılması

Bu proje final klinik segmentasyon ürünü olarak değerlendirilmemelidir.

Bu proje en doğru biçimde şu şekilde tanımlanabilir:

> **Bounding box rehberli mediastinal lezyon aday maske üretimi ve görselleştirme sistemi**

### MELA tarafında

- gerçek segmentation ground truth yoktur
- klasik Dice / IoU verilemez
- model çıktıları aday bölge olarak değerlendirilir

## 15. Bilinen Sınırlılıklar

- MELA üzerinde gerçek voxel seviyesinde ground truth yoktur.
- MELA için Dice / IoU doğrudan hesaplanamaz.
- Prediction kalitesi vakadan vakaya değişmektedir.
- Bazı vakalarda empty prediction oluşmaktadır.
- Bazı vakalarda over-segmentation görülmektedir.
- Model 2D slice-based yapıdadır, tam 3D model değildir.


###EN

# MediBox-Lesion

## 1. Project Overview

MediBox-Lesion is a medical image analysis project developed for mediastinal lesion analysis on 3D CT volumes.

Since the MELA dataset does not provide voxel-level ground truth masks, the project adopts a **bounding box guided candidate mask generation and visualization** approach.

The system is not positioned as a final clinical segmentation model. Instead, it is presented as a **lesion proposal / candidate mask generation research and demo prototype**.

---

## 2. Problem Definition

The MELA dataset contains:

- 3D CT volumes (`.nii.gz`)
- 3D bounding box annotations
- origin and spacing information

However, the dataset does not contain true voxel-level segmentation masks.

Because of this:

- classical supervised segmentation training cannot be directly applied
- standard segmentation metrics such as Dice and IoU cannot be reliably computed on MELA

To address this limitation, the project uses a **source-to-target transfer strategy**:

- A segmentation model is trained on **NSCLC-Radiomics**, where true tumor masks are available
- The trained model is then applied on **MELA** using bounding box guided inference
- The outputs are interpreted as **candidate lesion masks**, not final segmentations

---

## 3. Main Objectives

This project has three main objectives:

- Visualize mediastinal lesion regions on the MELA dataset
- Compare bounding box annotations with model-generated outputs
- Provide an interactive demo interface for live presentation and analysis

---

## 4. Datasets

### 4.1 MELA

This is the target dataset.

**Contents:**

- 3D CT volumes
- 3D bounding box annotations
- `coordX`, `coordY`, `coordZ`
- `x_length`, `y_length`, `z_length`
- origin and spacing information

**Limitations:**

- no true segmentation mask
- Dice / IoU cannot be directly computed

### 4.2 NSCLC-Radiomics

This is the source dataset.

**Contents:**

- thoracic CT volumes
- true tumor segmentation masks

**Purpose:**

- supervised model training
- quantitative evaluation
- transfer learning source domain

---

## 5. Project Approach

The project was developed in two major stages.

### 5.1 Stage 1 — Heuristic Pseudo-Mask Generation on MELA

A baseline pseudo-mask pipeline was first explored using:

- canonical orientation standardization
- annotation center transformation
- ROI extraction
- Gaussian smoothing
- center-guided seed selection
- intensity thresholding
- connected components
- morphology operations
- fallback inner box strategy

Although this pipeline was technically functional, the mask quality was inconsistent due to the anatomical complexity of the mediastinal region.

### 5.2 Stage 2 — Transfer Learning from NSCLC to MELA

In the second stage, a **SimpleUNet** model was trained on NSCLC with true masks and then applied on MELA using bbox-guided inference.

**General workflow:**

- model training on NSCLC
- loading MELA CT volumes
- extracting ROI using the bounding box
- ROI normalization
- slice-based model inference
- post-processing
- placing predictions back into the full volume
- visualization

---

## 6. Key Results

### 6.1 MELA Batch Inference Results

The model was applied to valid MELA cases with available CT images.

**Results:**

- Valid cases: 372
- Non-empty predictions: 324
- Empty predictions: 48

This shows that the model is able to produce non-empty candidate regions for many MELA cases.

However, prediction behavior varies from case to case:

- **empty** → no candidate region
- **small** → very small candidate region
- **medium** → moderate candidate region
- **large** → wide / over-segmented candidate region

### 6.2 NSCLC Quantitative Evaluation Results

Since NSCLC contains true masks, quantitative metrics were computed on this dataset.

**Validation results:**

- Mean Dice: 0.2514
- Mean IoU: 0.1598
- Mean Precision: 0.1935
- Mean Recall: 0.5207

**Interpretation:**

- the model can partially capture lesion regions
- recall is relatively higher
- precision is low
- the model tends to generate false positives
- it is not sufficient for final clinical segmentation

These findings support using the model on MELA as a candidate mask generator rather than a final segmentation system.

---

## 7. System Features

### 7.1 MELA Demo Interface

The Streamlit interface includes:

- manual case selection
- example group selection (`empty`, `small`, `medium`, `large`)
- automatic best slice selection
- bounding box visualization
- ROI visualization
- candidate mask overlay display
- mask-visible slice inspection
- previous / next case navigation

### 7.2 NSCLC Analysis

On the NSCLC side, the project supports:

- model training
- validation metric computation
- best / worst case analysis
- ground truth and prediction comparison

---

## 8. Repository Structure

```text
MediBox-Lesion/
├── app/
│   └── streamlit_app.py
├── data/
│   ├── mela/
│   └── nsclc/
├── docs/
├── notebooks/
│   ├── mela/
│   └── nsclc/
├── results/
├── tests/
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt

## 9. Important Notebooks

### MELA

- **`07_mela_single_case_model_inference.ipynb`**  
  Single-case inference

- **`08_mela_batch_model_inference.ipynb`**  
  Batch inference

- **`09_mela_prediction_visualization.ipynb`**  
  Visualization of selected cases

### NSCLC

- **`03_train_simple_unet.ipynb`**  
  Model training

- **`06_nsclc_model_evaluation.ipynb`**  
  Dice / IoU / Precision / Recall evaluation

---

## 10. Installation

### 10.1 Clone the repository

```bash
git clone <repo-link>
cd MediBox-Lesion


### 10.2 Create a virtual environment

```bash
python -m venv .venv

## 11. Data Setup

Due to large file sizes, medical images, masks, and model weights are not included in this repository.

To run the project, you must manually place the required files into the following directories.

### 11.1 Required MELA files

- `data/mela/annotations/mela_train_val_annotations.csv`
- `data/mela/annotations/mela_origin_spacing.csv`
- `data/mela/images/train/*.nii.gz`
- `data/mela/images/val/*.nii.gz`

### 11.2 Required NSCLC files

- `data/nsclc/images/*.npy`
- `data/nsclc/masks/*.npy`
- `data/nsclc/models/best_model.pt`
- `data/nsclc/metadata/val_patients.csv`

### 11.3 Required result files

- `results/mela_batch_inference_summary.csv`
- `results/mela_selected_example_cases.csv`
- `results/mela_batch_predictions/*.npy`

## 12. Running the Project

### 12.1 Launch the MELA demo interface

```bash
streamlit run app/streamlit_app.py

## 13. Documentation

Project documents are located in the `docs/` folder. This folder includes:

- Project proposal document
- Architecture document
- Technology stack document
- Installation guide
- API / module documentation
- User guide
- Developer guide
- Test report
- Final report
- Weekly reports

## 14. Project Positioning

This project should not be considered a final clinical segmentation product.

This project is most accurately defined as:

> **A bounding box-guided mediastinal lesion candidate mask generation and visualization system**

### On the MELA side

- there is no real segmentation ground truth
- classical Dice / IoU metrics cannot be reported
- model outputs are evaluated as candidate regions

## 15. Known Limitations

- There is no real voxel-level ground truth for MELA.
- Dice / IoU cannot be calculated directly for MELA.
- Prediction quality varies from case to case.
- Some cases produce empty predictions.
- Over-segmentation is observed in some cases.
- The model is based on 2D slices and is not a full 3D model.
