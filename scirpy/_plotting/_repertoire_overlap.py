import matplotlib.pyplot as plt
from anndata import AnnData
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.spatial import distance as sc_distance
from scipy.cluster import hierarchy as sc_hierarchy
from typing import Union, Sequence
from .._util import _is_na
from .. import tl
from ._styling import style_axes, DEFAULT_FIG_KWS, _init_ax
from ._base import ol_scatter


def repertoire_overlap(
    adata: AnnData,
    groupby: str,
    *,
    target_col: str = "clonotype",
    pair_to_plot: Union[None, Sequence[str]] = None,
    heatmap_cats: Union[None, Sequence[str]] = None,
    dendro_only: bool = False,
    overlap_measure: str = "jaccard",
    overlap_threshold: Union[None, float] = None,
    fraction: Union[None, str, bool] = None,
    added_key: str = "repertoire_overlap",
    **kwargs,
) -> plt.Axes:
    """Visualizes overlap betwen a pair of samples on a scatter plot or
    all samples on a heatmap or draws a dendrogram of samples only.
    
    Parameters
    ----------
    adata
        AnnData object to work on.
    groupby
        Column with group labels (e.g. samples, tissue source, diagnosis, etc).        
    target_col
        Category that overlaps among groups (`clonotype` by default, but can
        in principle be any group or cluster)
    pair_to_plot
        A tuple of two sample names that should be plotted on an IR overlap scatterplot.
    heatmap_cats
        Column names that should be shown as category on the side of the heatmap.
    dendro_only
        In case all samples are visualized, sets if a heatmap should be shown or only a dendrogram.
    overlap_measure
        Any distance measure accepted by `scipy.spatial.distance`; by default it is `jaccard`.
    overlap_threshold
        The minimum required weight to accept presence.
    fraction
        If `True`, compute fractions of abundances relative to the `groupby` column
        rather than reporting abosolute numbers. Alternatively, a column 
        name can be provided according to that the values will be normalized or an iterable
        providing cell weights directly. Setting it to `False` or `None` assigns equal weight
        to all cells.
    added_key
        If the tools has already been run, the results are added to `uns` under this key.
    **kwargs
        Additional arguments passed to the base plotting function.  
    
    Returns
    -------
    Axes object
    """

    if added_key not in adata.uns:
        tl.repertoire_overlap(
            adata,
            groupby=groupby,
            target_col=target_col,
            overlap_measure=overlap_measure,
            overlap_threshold=overlap_threshold,
            fraction=fraction,
        )
    df = adata.uns[added_key]["weighted"]

    if pair_to_plot is None:
        linkage = adata.uns[added_key]["linkage"]

        if heatmap_cats is not None:
            clust_colors, leg_colors = [], []
            for lbl in heatmap_cats:
                labels = adata.obs.groupby([groupby, lbl]).agg("size").reset_index()
                label_levels = labels[lbl].unique()
                label_pal = sns.cubehelix_palette(
                    label_levels.size,
                    light=0.7,
                    dark=0.3,
                    reverse=True,
                    start=2.5,
                    rot=-2,
                )
                colordict = dict(zip(label_levels, label_pal))
                for e in label_levels:
                    leg_colors.append((lbl + ": " + e, colordict[e]))
                labels[lbl] = labels[lbl].astype(str)
                labels[lbl] = labels.loc[:, lbl].map(colordict)
                clust_colors.append(labels[lbl])
                labels = labels.loc[:, [groupby, lbl]].set_index(groupby)
                colordict = labels.to_dict()
                colordict = colordict[lbl]

        if dendro_only:
            ax = _init_ax()
            sc_hierarchy.dendrogram(linkage, labels=df.index, ax=ax)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["bottom"].set_visible(False)
            ax.spines["left"].set_visible(False)
            if heatmap_cats is not None:
                for lbl in ax.get_xticklabels():
                    lbl.set_color(colordict[lbl.get_text()])
            ax.get_yaxis().set_ticks([])
        else:
            distM = adata.uns[added_key]["distance"]
            distM = sc_distance.squareform(distM)
            np.fill_diagonal(distM, 1)
            scaling_factor = distM.min()
            np.fill_diagonal(distM, scaling_factor)
            distM = pd.DataFrame(distM, index=df.index, columns=df.index)
            dd = sc_hierarchy.dendrogram(linkage, labels=df.index, no_plot=True)
            distM = distM.iloc[dd["leaves"], :]
            if heatmap_cats is None:
                ax = sns.clustermap(1 - distM, col_linkage=linkage, row_cluster=False)
            else:
                ax = sns.clustermap(
                    1 - distM,
                    col_linkage=linkage,
                    row_cluster=False,
                    row_colors=clust_colors,
                )
                lax = ax.ax_row_dendrogram
                for e, c in leg_colors:
                    lax.bar(0, 0, color=c, label=e, linewidth=0)
                lax.legend(loc="lower left")
            b, t = ax.ax_row_dendrogram.get_ylim()
            l, r = ax.ax_row_dendrogram.get_xlim()
            ax.ax_row_dendrogram.text(l, 0.9 * t, f"1-distance ({overlap_measure})")
    else:
        invalid_pair_warning = (
            "Did you supply two valid "
            + groupby
            + " names? Current indices are: "
            + ";".join(df.index.values)
        )
        valid_pairs = False
        try:
            o_df = df.loc[list(pair_to_plot), :].T
            valid_pairs = True
        except KeyError:
            print("One of the pair names not found in the database.")
        if valid_pairs:
            if o_df.shape[1] == 2:
                o_df = o_df.loc[(o_df.sum(axis=1) != 0), :]
                o_df = o_df.groupby(pair_to_plot).agg("size")
                o_df = o_df.reset_index()
                o_df.columns = ("x", "y", "z")
                o_df["z"] -= o_df["z"].min()
                o_df["z"] /= o_df["z"].max()
                o_df["z"] += 0.05
                o_df["z"] *= 1000

                # Create text for default labels
                p_a, p_b = pair_to_plot
                default_style_kws = {
                    "title": "Repertoire overlap between " + p_a + "and" + p_b,
                    "xlab": "Conotype size in " + p_a,
                    "ylab": "Conotype size in " + p_b,
                }
                if "style_kws" in kwargs:
                    default_style_kws.update(kwargs["style_kws"])
                kwargs["style_kws"] = default_style_kws
                ax = ol_scatter(o_df, **kwargs)
            else:
                raise TypeError(
                    "Wrong number of members. A pair is exactly two items! "
                    + invalid_pair_warning
                )
        else:
            raise TypeError(invalid_pair_warning)

    return ax
