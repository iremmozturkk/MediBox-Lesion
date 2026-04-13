from pathlib import Path
import numpy as np
import pandas as pd
import nibabel as nib
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import streamlit as st

st.set_page_config(page_title="MELA Candidate Mask Demo", layout="wide")

# ============================================================
# PATHS
# ============================================================
PROJECT_ROOT = Path(r"C:\Users\LENOVO\Desktop\3D-Lung-Lesion-Segmentation")

DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"

MELA_DIR = DATA_DIR / "mela"
ANNOT_DIR = MELA_DIR / "annotations"
IMG_DIR = MELA_DIR / "images"

BATCH_CSV_PATH = RESULTS_DIR / "mela_batch_inference_summary.csv"
EXAMPLE_CSV_PATH = RESULTS_DIR / "mela_selected_example_cases.csv"

# ============================================================
# LOADERS
# ============================================================
@st.cache_data
def load_tables():
    ann_df = pd.read_csv(ANNOT_DIR / "mela_train_val_annotations.csv")
    spacing_df = pd.read_csv(ANNOT_DIR / "mela_origin_spacing.csv")
    batch_df = pd.read_csv(BATCH_CSV_PATH)
    merged_df = ann_df.merge(spacing_df, on="public_id", how="left")

    if EXAMPLE_CSV_PATH.exists():
        example_df = pd.read_csv(EXAMPLE_CSV_PATH)
    else:
        example_df = None

    return merged_df, batch_df, example_df


def find_image_path(public_id, img_root):
    img_root = Path(img_root)

    candidate_patterns = [
        img_root / "train" / f"{public_id}.nii.gz",
        img_root / "val" / f"{public_id}.nii.gz",
        img_root / f"{public_id}.nii.gz",
        img_root / "train" / f"{public_id}.nii",
        img_root / "val" / f"{public_id}.nii",
        img_root / f"{public_id}.nii",
    ]

    for p in candidate_patterns:
        if p.exists():
            return p

    matches = list(img_root.rglob(f"{public_id}*"))
    if len(matches) > 0:
        return matches[0]

    return None


@st.cache_data
def load_volume(public_id):
    img_path = find_image_path(public_id, IMG_DIR)
    if img_path is None:
        raise FileNotFoundError(f"Image not found for {public_id}")

    nii = nib.load(str(img_path))
    vol_xyz = nii.get_fdata()
    volume = np.transpose(vol_xyz, (2, 1, 0)).astype(np.float32)  # (Z, Y, X)
    return volume, str(img_path)


@st.cache_data
def load_prediction(pred_path_str):
    pred_path = Path(pred_path_str)
    if not pred_path.exists():
        raise FileNotFoundError(f"Prediction not found: {pred_path}")
    return np.load(pred_path)


def get_annotation_row(public_id, merged_df):
    row = merged_df[merged_df["public_id"] == public_id]
    if len(row) == 0:
        raise ValueError(f"Annotation row not found for {public_id}")
    return row.iloc[0].copy()


def get_batch_row(public_id, batch_df):
    row = batch_df[batch_df["public_id"] == public_id]
    if len(row) == 0:
        raise ValueError(f"Batch row not found for {public_id}")
    return row.iloc[0].copy()


def compute_bbox_coords(sample_row, volume_shape, roi_margin=10):
    cx = int(round(sample_row["coordX"]))
    cy = int(round(sample_row["coordY"]))
    cz = int(round(sample_row["coordZ"]))

    lx = int(round(sample_row["x_length"]))
    ly = int(round(sample_row["y_length"]))
    lz = int(round(sample_row["z_length"]))

    # true bbox
    bx1 = max(0, cx - lx // 2)
    bx2 = min(volume_shape[2], cx + lx // 2)

    by1 = max(0, cy - ly // 2)
    by2 = min(volume_shape[1], cy + ly // 2)

    bz1 = max(0, cz - lz // 2)
    bz2 = min(volume_shape[0], cz + lz // 2)

    # ROI bbox
    rx1 = max(0, cx - lx // 2 - roi_margin)
    rx2 = min(volume_shape[2], cx + lx // 2 + roi_margin)

    ry1 = max(0, cy - ly // 2 - roi_margin)
    ry2 = min(volume_shape[1], cy + ly // 2 + roi_margin)

    rz1 = max(0, cz - lz // 2 - roi_margin)
    rz2 = min(volume_shape[0], cz + lz // 2 + roi_margin)

    return {
        "cx": cx, "cy": cy, "cz": cz,
        "lx": lx, "ly": ly, "lz": lz,
        "bx1": bx1, "bx2": bx2,
        "by1": by1, "by2": by2,
        "bz1": bz1, "bz2": bz2,
        "rx1": rx1, "rx2": rx2,
        "ry1": ry1, "ry2": ry2,
        "rz1": rz1, "rz2": rz2,
    }


def get_nonzero_slices(mask_3d):
    return np.where(mask_3d.reshape(mask_3d.shape[0], -1).sum(axis=1) > 0)[0]


def get_best_slice(pred_3d, fallback_slice):
    slice_sums = pred_3d.reshape(pred_3d.shape[0], -1).sum(axis=1)
    if slice_sums.max() > 0:
        return int(np.argmax(slice_sums))
    return int(fallback_slice)


def choose_visible_slices(pred_3d, fallback_slice):
    nz = get_nonzero_slices(pred_3d)
    if len(nz) == 0:
        return [int(fallback_slice)]
    if len(nz) == 1:
        return [int(nz[0])]
    if len(nz) == 2:
        return [int(nz[0]), int(nz[1])]
    return [int(nz[0]), int(nz[len(nz)//2]), int(nz[-1])]


def classify_prediction(pred_sum, empty_prediction):
    if empty_prediction == 1 or pred_sum == 0:
        return "empty"
    if pred_sum < 100:
        return "small"
    if pred_sum > 100000:
        return "large"
    return "medium"


def prediction_type_html(pred_type):
    color_map = {
        "empty": "#ff4b4b",
        "small": "#ff9f1a",
        "medium": "#3b82f6",
        "large": "#a855f7",
    }
    text_map = {
        "empty": "No candidate region",
        "small": "Tiny candidate region",
        "medium": "Moderate candidate region",
        "large": "Wide / over-segmented region",
    }
    color = color_map.get(pred_type, "#888888")
    text = text_map.get(pred_type, pred_type)

    return f"""
    <div style="
        padding: 12px 16px;
        border-radius: 12px;
        background: rgba(255,255,255,0.04);
        border-left: 6px solid {color};
        margin-bottom: 8px;
    ">
        <div style="font-size: 14px; opacity: 0.8;">Prediction interpretation</div>
        <div style="font-size: 20px; font-weight: 700; color: {color};">{pred_type.upper()}</div>
        <div style="font-size: 15px; opacity: 0.9;">{text}</div>
    </div>
    """


def make_main_figure(ct_slice, pred_slice, bbox_coords, slice_idx, public_id,
                     show_true_bbox=True, show_roi_box=True):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    axes[0].imshow(ct_slice, cmap="gray")
    axes[0].set_title(f"{public_id} | slice {slice_idx} | CT Slice")
    axes[0].axis("off")

    axes[1].imshow(ct_slice, cmap="gray")
    axes[1].set_title("Annotation Box")
    axes[1].axis("off")

    if show_true_bbox:
        rect_true = patches.Rectangle(
            (bbox_coords["bx1"], bbox_coords["by1"]),
            bbox_coords["bx2"] - bbox_coords["bx1"],
            bbox_coords["by2"] - bbox_coords["by1"],
            linewidth=2,
            edgecolor="cyan",
            facecolor="none",
        )
        axes[1].add_patch(rect_true)

    if show_roi_box:
        rect_roi = patches.Rectangle(
            (bbox_coords["rx1"], bbox_coords["ry1"]),
            bbox_coords["rx2"] - bbox_coords["rx1"],
            bbox_coords["ry2"] - bbox_coords["ry1"],
            linewidth=2,
            edgecolor="yellow",
            facecolor="none",
        )
        axes[1].add_patch(rect_roi)

    axes[2].imshow(ct_slice, cmap="gray")
    axes[2].imshow(pred_slice, cmap="Reds", alpha=0.35)
    axes[2].set_title("Model Overlay")
    axes[2].axis("off")

    if show_true_bbox:
        rect_true2 = patches.Rectangle(
            (bbox_coords["bx1"], bbox_coords["by1"]),
            bbox_coords["bx2"] - bbox_coords["bx1"],
            bbox_coords["by2"] - bbox_coords["by1"],
            linewidth=2,
            edgecolor="cyan",
            facecolor="none",
        )
        axes[2].add_patch(rect_true2)

    if show_roi_box:
        rect_roi2 = patches.Rectangle(
            (bbox_coords["rx1"], bbox_coords["ry1"]),
            bbox_coords["rx2"] - bbox_coords["rx1"],
            bbox_coords["ry2"] - bbox_coords["ry1"],
            linewidth=2,
            edgecolor="yellow",
            facecolor="none",
        )
        axes[2].add_patch(rect_roi2)

    plt.tight_layout()
    return fig


def make_visible_slices_figure(volume, pred_3d, bbox_coords, selected_slices, public_id,
                               show_true_bbox=True, show_roi_box=True):
    fig, axes = plt.subplots(1, len(selected_slices), figsize=(5 * len(selected_slices), 5))
    if len(selected_slices) == 1:
        axes = [axes]

    for ax, sidx in zip(axes, selected_slices):
        ax.imshow(volume[sidx], cmap="gray")
        ax.imshow(pred_3d[sidx], cmap="Reds", alpha=0.35)
        ax.set_title(f"{public_id} | slice {sidx}")
        ax.axis("off")

        if show_true_bbox:
            rect_true = patches.Rectangle(
                (bbox_coords["bx1"], bbox_coords["by1"]),
                bbox_coords["bx2"] - bbox_coords["bx1"],
                bbox_coords["by2"] - bbox_coords["by1"],
                linewidth=2,
                edgecolor="cyan",
                facecolor="none",
            )
            ax.add_patch(rect_true)

        if show_roi_box:
            rect_roi = patches.Rectangle(
                (bbox_coords["rx1"], bbox_coords["ry1"]),
                bbox_coords["rx2"] - bbox_coords["rx1"],
                bbox_coords["ry2"] - bbox_coords["ry1"],
                linewidth=2,
                edgecolor="yellow",
                facecolor="none",
            )
            ax.add_patch(rect_roi)

    plt.tight_layout()
    return fig


# ============================================================
# APP
# ============================================================
st.title("MELA Lesion Proposal Demo")
st.caption("NSCLC üzerinde eğitilen modelin MELA vakalarında aday maske üretiminin görselleştirilmesi")

merged_df, batch_df, example_df = load_tables()

ok_df = batch_df[batch_df["status"] == "ok"].copy()
empty_df = ok_df[ok_df["empty_prediction"] == 1].copy()
non_empty_df = ok_df[ok_df["empty_prediction"] == 0].copy()

with st.sidebar:
    st.header("Controls")

    mode = st.radio(
        "Selection mode",
        ["Manual", "Example group"] if example_df is not None else ["Manual"],
        index=0
    )

    if mode == "Manual":
        filter_mode = st.selectbox(
            "Case filter",
            ["All OK", "Non-empty only", "Empty only"]
        )

        if filter_mode == "All OK":
            select_df = ok_df.copy()
        elif filter_mode == "Non-empty only":
            select_df = non_empty_df.copy()
        else:
            select_df = empty_df.copy()

        case_list = select_df["public_id"].tolist()

        if "selected_case_idx" not in st.session_state:
            st.session_state.selected_case_idx = 0

        st.session_state.selected_case_idx = min(st.session_state.selected_case_idx, len(case_list) - 1)
        public_id = case_list[st.session_state.selected_case_idx]

        public_id = st.selectbox(
            "Select public_id",
            case_list,
            index=st.session_state.selected_case_idx
        )
        st.session_state.selected_case_idx = case_list.index(public_id)

        prev_col, next_col = st.columns(2)
        with prev_col:
            if st.button("◀ Previous"):
                st.session_state.selected_case_idx = max(0, st.session_state.selected_case_idx - 1)
                st.rerun()

        with next_col:
            if st.button("Next ▶"):
                st.session_state.selected_case_idx = min(len(case_list) - 1, st.session_state.selected_case_idx + 1)
                st.rerun()

    else:
        available_groups = sorted(example_df["example_group"].dropna().unique().tolist())
        group_name = st.selectbox("Example group", available_groups)
        group_df = example_df[example_df["example_group"] == group_name].reset_index(drop=True)

        row_idx = st.slider("Example index", 0, max(len(group_df) - 1, 0), 0)
        public_id = group_df.iloc[row_idx]["public_id"]

    roi_margin = st.slider("ROI margin", min_value=0, max_value=30, value=10, step=1)
    show_true_bbox = st.checkbox("Show true bbox", value=True)
    show_roi_box = st.checkbox("Show ROI box", value=True)

try:
    batch_row = get_batch_row(public_id, batch_df)
    ann_row = get_annotation_row(public_id, merged_df)
    volume, img_path = load_volume(public_id)
    pred_3d = load_prediction(batch_row["pred_path"])
    bbox_coords = compute_bbox_coords(ann_row, volume.shape, roi_margin=roi_margin)

    fallback_slice = int(np.clip(bbox_coords["cz"], 0, volume.shape[0] - 1))
    best_slice = get_best_slice(pred_3d, fallback_slice)
    visible_slices = choose_visible_slices(pred_3d, fallback_slice)

    pred_sum = int(pred_3d.sum())
    empty_prediction = int(batch_row["empty_prediction"])
    pred_type = classify_prediction(pred_sum, empty_prediction)

    st.subheader(f"Case: {public_id}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Prediction volume", pred_sum)
    c2.metric("Prediction type", pred_type)
    c3.metric("Mask slices", len(get_nonzero_slices(pred_3d)))

    st.markdown(prediction_type_html(pred_type), unsafe_allow_html=True)

    with st.expander("Case details", expanded=False):
        st.write("Image path:", img_path)
        st.write("Prediction path:", batch_row["pred_path"])
        st.write("BBox center:", (bbox_coords["cx"], bbox_coords["cy"], bbox_coords["cz"]))
        st.write("BBox size:", (bbox_coords["lx"], bbox_coords["ly"], bbox_coords["lz"]))

    slice_mode = st.radio(
        "Slice mode",
        ["Best slice", "Manual"],
        horizontal=True
    )

    if slice_mode == "Best slice":
        slice_idx = best_slice
        st.info(f"Best slice selected automatically: {best_slice}")
    else:
        slice_idx = st.slider("Slice index", 0, volume.shape[0] - 1, best_slice)

    fig_main = make_main_figure(
        ct_slice=volume[slice_idx],
        pred_slice=pred_3d[slice_idx],
        bbox_coords=bbox_coords,
        slice_idx=slice_idx,
        public_id=public_id,
        show_true_bbox=show_true_bbox,
        show_roi_box=show_roi_box,
    )
    st.pyplot(fig_main, clear_figure=True)

    st.markdown("### Mask-visible slices")

    if pred_type == "empty":
        st.warning("Bu vakada model boş prediction üretti.")
    else:
        
        fig_visible = make_visible_slices_figure(
            volume=volume,
            pred_3d=pred_3d,
            bbox_coords=bbox_coords,
            selected_slices=visible_slices,
            public_id=public_id,
            show_true_bbox=show_true_bbox,
            show_roi_box=show_roi_box,
        )
        st.pyplot(fig_visible, clear_figure=True)

except Exception as e:
    st.error(f"Error while loading case: {e}")