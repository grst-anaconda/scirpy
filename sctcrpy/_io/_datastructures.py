"""Datastructures for TCR data. 

Currently only used as intermediate storage. 
See also discussion at https://github.com/theislab/anndata/issues/115
"""

from .._compat import Literal


class TcrChain:
    def __init__(
        self,
        chain_type: Literal["TRA", "TRB", "other"],
        *,
        cdr3: str = None,
        cdr3_nt: str = None,
        expr: float = None,
        expr_raw: float = None,
        is_productive: bool = None,
        v_gene: str = None,
        d_gene: str = None,
        j_gene: str = None,
        c_gene: str = None,
        junction_ins: int = None,
    ):
        """Data structure for a T cell receptor chain. 
        
        Parameters
        ----------
        chain_type 
            Currently supported: ["TRA", "TRB", "other"]        
        cdr3 
            Amino acid sequence of the CDR3 region 
        cd3_nt 
            Nucleotide sequence fo the CDR3 region 
        expr 
            Normalized read count for the CDR3 region. 
            Will be UMIs for 10x and TPM for SmartSeq2. 
        expr_raw
            Raw read count for the CDR3 regions.
        is_productive 
            Is the chain productive?
        v_gene
            gene symbol of v gene
        d_gene
            gene symbol of d gene
        j_gene
            gene symbol of j gene
        c_gene
            gene symbol of c gene
        junction_ins
            nucleotides inserted in the junctions. 
            For type == TRA: nucleotides inserted in the VJ junction
            For type == TRB: sum of nucleotides inserted in the VD + DJ junction
        """
        if chain_type not in ["TRA", "TRB", "other"]:
            raise ValueError("Invalid chain type: {}".format(chain_type))

        self.chain_type = chain_type
        self.cdr3 = cdr3.upper() if cdr3 is not None else None
        self.cdr3_nt = cdr3_nt.upper() if cdr3_nt is not None else None
        self.expr = expr
        self.expr_raw = expr_raw
        self.is_productive = is_productive
        self.v_gene = v_gene
        self.d_gene = d_gene
        self.j_gene = j_gene
        self.c_gene = c_gene
        self.junction_ins = junction_ins

    def __repr__(self):
        return "TcrChain object: " + str(self.__dict__)

    @property
    def cdr3_len(self):
        return len(self.cdr3) if self.cdr3 is not None else None


class TcrCell:
    def __init__(self, cell_id: str):
        """Data structure for a Cell with TCR receptors. 

        A TcrCell can hold multiple TcrChains. 

        Parameters
        ----------
        cell_id 
            cell id or barcode.  
        """
        self._cell_id = cell_id
        self.chains = list()

    def __repr__(self):
        return "TcrCell {} with {} chains".format(self._cell_id, len(self.chains))

    @property
    def cell_id(self):
        return self._cell_id

    def add_chain(self, chain: TcrChain):
        self.chains.append(chain)