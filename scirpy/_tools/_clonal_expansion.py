from anndata import AnnData
from typing import Dict
from .._util import _is_na, _normalize_counts
import numpy as np
import pandas as pd
from typing import Union
from .._compat import Literal


def _clip_and_count(
    adata: AnnData,
    target_col: str,
    *,
    groupby: Union[str, None] = None,
    clip_at: int = 3,
    inplace: bool = True,
    key_added: Union[str, None] = None,
    fraction: bool = True,
) -> Union[None, np.ndarray]:
    """Counts the number of identical entries in `target_col` 
    for each group in `group_by`. 
    """
    if target_col not in adata.obs.columns:
        raise ValueError("`target_col` not found in obs.")

    groupby = [groupby] if isinstance(groupby, str) else groupby
    groupby_cols = [target_col] if groupby is None else groupby + [target_col]
    clonotype_counts = (
        adata.obs.groupby(groupby_cols, observed=True)
        .size()
        .reset_index(name="tmp_count")
        .assign(
            tmp_count=lambda X: [
                ">= {}".format(min(n, clip_at)) if n >= clip_at else str(n)
                for n in X["tmp_count"].values
            ]
        )
    )
    clipped_count = adata.obs.merge(clonotype_counts, how="left", on=groupby_cols)[
        "tmp_count"
    ].values

    if inplace:
        key_added = (
            "{}_clipped_count".format(target_col) if key_added is None else key_added
        )
        adata.obs[key_added] = clipped_count
    else:
        return clipped_count


def clonal_expansion(
    adata: AnnData,
    *,
    target_col: str = "clonotype",
    expanded_in: Union[str, None] = None,
    clip_at: int = 3,
    key_added: str = "clonal_expansion",
    inplace: bool = True,
) -> Union[None, np.ndarray]:
    """Adds a column to obs which clonotypes are expanded. 
    
    Counts NaN values like any other value in `target_col`. 

    Parameters
    ----------
    adata
        Annoated data matrix
    target_col
        Column containing the clontype annoataion
    expanded_in
        Calculate clonal expansion within groups. Usually makes sense to set
        this to the column containing sample annotation. If set to None, 
        a clonotype counts as expanded if there's any cell of the same clonotype
        across the entire dataset. 
    clip_at:
        All clonotypes with more than `clip_at` clones will be summarized into 
        a single category
    key_added
        Key under which the results will be added to `obs`. 
        Additional arguments passed to :func:`scirpy.tl.clip_and_count`.
    inplace
        If True, adds a column to `obs`. Otherwise returns an array 
        with the clipped counts. 

    Returns
    -------
    Depending on the value of inplace, adds a column to adata or returns
    an array with the clipped count per cell. 
    """
    return _clip_and_count(
        adata,
        target_col,
        groupby=expanded_in,
        clip_at=clip_at,
        key_added=key_added,
        inplace=inplace,
    )


def summarize_clonal_expansion(
    adata: AnnData,
    groupby: str,
    *,
    target_col: str = "clonotype",
    summarize_by: Literal["cell", "clonotype"] = "cell",
    normalize: Union[bool] = False,
    **kwargs,
):
    """
    Summarizes clonal expansion by a grouping variable. 

    Removes all entries with `NaN` in `target_col` prior to plotting. 

    Parameters
    ----------
    adata
        annotated data matrix
    groupby
        summarize by this column in `adata.obs`. 
    target_col
        column in obs which holds the clonotype information
    summarize_by
        Can be either `cell` to count cells belonging to a clonotype (the default),
        or "clonotype" to count clonotypes. The former leads to a over-representation
        of expanded clonotypes but better represents the fraction of expanded cells. 
    normalize
        If False, plot absolute cell counts. If True, scale each group to 1. 
    **kwargs
        Additional arguments passed to :func:`clonal_expansion`. 
    
    Returns
    -------
    pd.DataFrame 
    """
    if summarize_by not in ["clonotype", "cell"]:
        raise ValueError("Invalue value for `summarize_by`. ")

    expansion = clonal_expansion(adata, target_col=target_col, inplace=False, **kwargs)

    tmp_col = target_col + "_clipped_count"
    tmp_col_weight = target_col + "_weight"

    obs = adata.obs.loc[:, [groupby, target_col]]
    obs[tmp_col] = expansion

    # filter NA values
    obs = obs.loc[~_is_na(obs[target_col]), :]

    if summarize_by == "clonotype":
        obs.drop_duplicates(inplace=True)

    # add normalization vector
    size_vector = _normalize_counts(obs, normalize, groupby)
    obs[tmp_col_weight] = size_vector

    obs = (
        obs.groupby([groupby, tmp_col], observed=True)[tmp_col_weight]
        .sum()
        .reset_index()
        .pivot(index=groupby, columns=tmp_col, values=tmp_col_weight)
        .fillna(0)
    )

    return obs
