#/***********************************************************************
# * Licensed Materials - Property of IBM 
# *
# * IBM SPSS Products: Statistics Common
# *
# * (C) Copyright IBM Corp. 1989, 2016
# *
# * US Government Users Restricted Rights - Use, duplication or disclosure
# * restricted by GSA ADP Schedule Contract with IBM Corp. 
# ************************************************************************/

from __future__ import with_statement

"""STATS CORRELATIONS extension command"""

__author__ =  'JKP'
__version__=  '1.0.0'

# history
# 08-jul-2016 original version




import spss, spssaux, spssdata
from extension import Template, Syntax, processcmd
from spss import CellText, FormatSpec
import  random, math, copy


def docorr(variables, withvars=None, clevel=95, method="fisher", include=False, exclude=False,
    listwise=False, pairwise=False):
    """Calculate confidence intervals for correlations based on CORRELATION output"""

    activeds = spss.ActiveDataset()
    if activeds == "*":
        raise ValueError(_("""The active dataset must have a dataset name to use this procedure"""))
    if listwise and pairwise:
        raise ValueError(_("""Cannot specify both listwise and pairwise deletion"""))
    missing = listwise and "LISTWISE" or "PAIRWISE"
    if include and exclude:
        raise ValueError(_("""Cannot specify both include and exclude missing values"""))
    inclusion = include and "INCLUDE" or "EXCLUDE"
    allvars = " ".join(variables)
    if withvars:
        allvars2 = allvars + " " + " ".join(withvars)    
        allvarswith = allvars + " WITH " + " ".join(withvars)
    else:
        allvarswith = allvars
        allvars2 = allvars
    if method == "bootstrap":
        spss.Submit(r"""PRESERVE.
SET RNG=MT.
BOOTSTRAP /VARIABLES INPUT = %(allvars2)s
/CRITERIA CILEVEL=%(clevel)s CITYPE=PERCENTILE NSAMPLES=1000.
CORRELATIONS
  /VARIABLES = %(allvarswith)s
  /PRINT=NOSIG
  /MISSING=%(missing)s %(inclusion)s.
RESTORE.""" % locals())
        return
    # regular CIs
    dsname = "D" +str(random.uniform(.05, 1.))
    omstag = "O" + str(random.uniform(.05, 1.))

    # run CORRELATIONS with MATRIX output.
    # Validation of variable list requirements is handled
    # by CORRELATIONS.
    try:
        failed = False
        spss.Submit(r"""oms /select all except = warnings/destination viewer=no
    /tag = "%(omstag)s".
    dataset declare %(dsname)s.
    correlations /variables = %(allvars2)s
    /missing=%(missing)s %(inclusion)s
    /matrix=out(%(dsname)s).
    """ % locals())
    except spss.SpssError:
        failed = True
    finally:
        spss.Submit("""omsend tag=%(omstag)s""" % locals())
    if failed:
        return 
    spss.Submit("dataset activate %(dsname)s." % locals())
    spss.Submit("""select if ROWTYPE_ eq "N" or ROWTYPE_ eq "CORR".""")
    spss.Submit("""sort cases by VARNAME_.""")
    #dictionary of variable names in matrix dataset
    matnames = dict([(spss.GetVariableName(i), i) for i in range(spss.GetVariableCount())])
    rowtypeloc = matnames["ROWTYPE_"]
    curs = spssdata.Spssdata()
    stats = []
    uppervariables = [v.upper() for v in variables]

    for i, case in enumerate(curs):
        if case.ROWTYPE_.rstrip() == "N":
            N = case[rowtypeloc+2:]
        # screen out rows for any WITH variables
        if case[rowtypeloc+1].upper().rstrip() not in uppervariables:
            continue
        if case.ROWTYPE_.rstrip() == "CORR":
            CORR = case[rowtypeloc+2:]
            dta = cidata(splitvars=case[0:rowtypeloc],
                variable=case[rowtypeloc+1],
                ns = N,
                corrs = CORR,
                cis = ci(N, CORR, clevel/100.)
            )
            stats.append(dta)

    curs.CClose()
    spss.Submit("""dataset activate %(activeds)s.
    dataset close %(dsname)s.""" % locals())
    
    display(variables, withvars, stats, matnames, clevel, missing, inclusion)
    
    
class cidata(object):
    """construct rows for pivot table display"""
    
    def __init__(self, splitvars, variable, ns, corrs, cis):
        self.splitvars = [CellText.String(v) for v in splitvars]
        self.variable = CellText.String(variable)
        self.ns = [CellText.Number(n, FormatSpec.Count) for n in ns]
        
        self.corrs = []
        for c in corrs:
            if c is None:
                self.corrs.append(CellText.String("--"))
            else:
                self.corrs.append(CellText.Number(c, FormatSpec.Correlation))
                
        self.cis = []
        for v in cis:
            pair = [CellText.String("--"), CellText.String("--")]
            for i in range(2):
                if v[i] is not None:
                    pair[i] = CellText.Number(v[i], FormatSpec.Correlation)
            self.cis.append(pair)
    
    def __len__(self):
        return len(self.ns)
    
def ci(n, corr, clevel):
    """return clevel-% lower and upper confidence levels for each pair
    
    n and corr are vectors of counts and correlations
    Correlations very close to +-1 do not get a CI
    """
    
    critz = abs(idfNormal((1-clevel)/2))
    res = []
    for nn, cc in zip(n, corr):
        if nn <=3 or cc is None or abs(abs(cc)-1) < 1e-12:   # fuzz factor because of floating point properties
            res.append((None, None))
        else:
            try:
                Z = math.atanh(cc)
                zse = critz/math.sqrt(nn-3)
                lowci = (math.tanh(Z) - math.tanh(zse)) / (1 - math.tanh(Z) * math.tanh(zse))
                upperci = (math.tanh(Z) + math.tanh(zse)) / (1 + math.tanh(Z) * math.tanh(zse))
                res.append((lowci, upperci))
            except:
                res.append((None, None))
    return res

def display(variables, withvars, stats, matnames, clevel, missing, inclusion):
    """Display pivot table output for regular or split files
    variables is the main variable list
    withvars is None or a list of variables to correlate with
    stats is the result structure
    clevel is the confidence level
    missing is listwise or pairwise
    include is include or exclude for user missing values"""
    
    spss.StartProcedure(_("Correlations"), "CICORRELATIONS")
    tbl = spss.BasePivotTable(_("Correlations"), "CICORRELATIONS")
    tbl.Caption(_("""Missing value handling: %s, %s.  C.I. Level: %s""") % (missing, inclusion, clevel))
    rowsplits = []
    for v in spss.GetSplitVariableNames():
        rowsplits.append(tbl.Append(spss.Dimension.Place.row, v))
    nsplitvars = len(rowsplits)
    var1 = tbl.Append(spss.Dimension.Place.row, _("Variable"))
    var2 = tbl.Append(spss.Dimension.Place.row, _("Variable2"))
    vlist = withvars and withvars or variables
    col1 = tbl.Append(spss.Dimension.Place.column, _("Statistic"))
    tbl.SetCategories(col1, [CellText.String(_("Correlation")), CellText.String(_("Count")), 
        CellText.String(_("Lower C.I.")), CellText.String(_("Upper C.I.")), CellText.String(_("Notes"))])
    
    
    for vcount, s in enumerate(stats):
        for i, vv in enumerate(vlist):
            j = i + (withvars is not None and len(variables))
            if nsplitvars > 0:
                rows = copy.copy(s.splitvars)
            else:
                rows = []                
            rows.append(s.variable)
            rows.append(CellText.String(vv))
            if s.ns[j].toNumber() > 10:
                note = ""
            elif s.ns[j].toNumber() <= 3:
                note = _("Some items not computed")
            else:
                note = _("Normality assumption is not accurate")
            statsi = [s.corrs[j], s.ns[j], s.cis[j][0], s.cis[j][1], CellText.String(note)]
            tbl.SetCellsByRow(rows, statsi)
            ###tbl.SetCellsByRow(rows, [Ctn(item) for item in statsi])
    spss.EndProcedure()

    
# CellText.Number for NaN values
class Ctn(object):
    def __init__(self, value):
        self.data = {}
        self.data["type"] = 0
        self.data["value"] = value
        self.data["format"] = CellText._CellText__defaultFormatSpec        
# public domain code: http://www.johndcook.com/blog/python_phi_inverse/

def rational_approximation(t):

    # Abramowitz and Stegun formula 26.2.23.
    # The absolute value of the error should be less than 4.5 e-4.
    c = [2.515517, 0.802853, 0.010328]
    d = [1.432788, 0.189269, 0.001308]
    numerator = (c[2]*t + c[1])*t + c[0]
    denominator = ((d[2]*t + d[1])*t + d[0])*t + 1.0
    return t - numerator / denominator


# Paul M. Voutier, A New Approximation to the Normal
# Distribution Quantile Function

def better_rational_approximation(t):
    c0 = 2.653962002601684482
    c1 = 1.561533700212080345
    c2 = 0.061146735765196993
    d1 = 1.904875182836498708
    d2 = 0.454055536444233510
    d3 = 0.009547745327068945
    
    numerator = c2*t*t + c1 * t + c0
    denominator = d3 * t*t*t + d2*t*t + d1* t + 1
    return t - numerator / denominator

def idfNormal(p):

    assert p > 0.0 and p < 1

    # See article above for explanation of this section.
    if p < 0.5:
        # F^-1(p) = - G^-1(p)
        return -better_rational_approximation( math.sqrt(-2.0*math.log(p)) )
    else:
        # F^-1(p) = G^-1(1-p)
        return better_rational_approximation( math.sqrt(-2.0*math.log(1.0-p)) )
        

    
   
def Run(args):
    """Execute the STATS CORRELATIONS extension command"""

    args = args[args.keys()[0]]
    # debugging
    # makes debug apply only to the current thread
    #try:
        #import wingdbstub
        #if wingdbstub.debugger != None:
            #import time
            #wingdbstub.debugger.StopDebug()
            #time.sleep(2)
            #wingdbstub.debugger.StartDebug()
        #import thread
        #wingdbstub.debugger.SetDebugThreads({thread.get_ident(): 1}, default_policy=0)
        ## for V19 use
        ##    ###SpssClient._heartBeat(False)
    #except:
        #print 'debug failed'

    oobj = Syntax([

        Template("VARIABLES", subc="",  ktype="existingvarlist", var="variables", islist=True),
        
        Template("VARIABLES", subc="WITH", ktype="existingvarlist", var="withvars", islist=True),
        
        Template("CONFLEVEL", subc="OPTIONS", ktype="float", var="clevel", vallist=(25., 99.999)),
        Template("METHOD", subc="OPTIONS", ktype="str", var="method", vallist=("fisher", "bootstrap")),
        
        Template("LISTWISE", subc="MISSING",  ktype="bool", var="listwise"),
        Template("PAIRWISE", subc="MISSING", ktype="bool", var="pairwise"),
        Template("INCLUDE", subc="MISSING", ktype="bool", var="include"),
        Template("EXCLUDE", subc="MISSING", ktype="bool", var="exclude"),    
        Template("HELP", subc="", ktype="bool")])
    
    #enable localization
    global _
    try:
        _("---")
    except:
        def _(msg):
            return msg
    # A HELP subcommand overrides all else
    if args.has_key("HELP"):
        #print helptext
        helper()
    else:
        processcmd(oobj, args, docorr, vardict=spssaux.VariableDict())

def helper():
    """open html help in default browser window
    
    The location is computed from the current module name"""
    
    import webbrowser, os.path
    
    path = os.path.splitext(__file__)[0]
    helpspec = "file://" + path + os.path.sep + \
         "markdown.html"
    
    # webbrowser.open seems not to work well
    browser = webbrowser.get()
    if not browser.open_new(helpspec):
        print("Help file not found:" + helpspec)
        
class NonProcPivotTable(object):
    """Accumulate an object that can be turned into a basic pivot table once a procedure state can be established"""
    
    def __init__(self, omssubtype, outlinetitle="", tabletitle="", caption="", rowdim="", coldim="", columnlabels=[],
                 procname="Messages"):
        """omssubtype is the OMS table subtype.
        caption is the table caption.
        tabletitle is the table title.
        columnlabels is a sequence of column labels.
        If columnlabels is empty, this is treated as a one-column table, and the rowlabels are used as the values with
        the label column hidden
        
        procname is the procedure name.  It must not be translated."""
        
        attributesFromDict(locals())
        self.rowlabels = []
        self.columnvalues = []
        self.rowcount = 0

    def addrow(self, rowlabel=None, cvalues=None):
        """Append a row labelled rowlabel to the table and set value(s) from cvalues.
        
        rowlabel is a label for the stub.
        cvalues is a sequence of values with the same number of values are there are columns in the table."""

        if cvalues is None:
            cvalues = []
        self.rowcount += 1
        if rowlabel is None:
            self.rowlabels.append(str(self.rowcount))
        else:
            self.rowlabels.append(rowlabel)
        self.columnvalues.extend(cvalues)
        
    def generate(self):
        """Produce the table assuming that a procedure state is now in effect if it has any rows."""
        
        privateproc = False
        if self.rowcount > 0:
            try:
                table = spss.BasePivotTable(self.tabletitle, self.omssubtype)
            except:
                StartProcedure(_("Adjust Widths"), self.procname)
                privateproc = True
                table = spss.BasePivotTable(self.tabletitle, self.omssubtype)
            if self.caption:
                table.Caption(self.caption)
            if self.columnlabels != []:
                table.SimplePivotTable(self.rowdim, self.rowlabels, self.coldim, self.columnlabels, self.columnvalues)
            else:
                table.Append(spss.Dimension.Place.row,"rowdim",hideName=True,hideLabels=True)
                table.Append(spss.Dimension.Place.column,"coldim",hideName=True,hideLabels=True)
                colcat = spss.CellText.String("Message")
                for r in self.rowlabels:
                    cellr = spss.CellText.String(r)
                    table[(cellr, colcat)] = cellr
            if privateproc:
                spss.EndProcedure()
                
def attributesFromDict(d):
    """build self attributes from a dictionary d."""
    self = d.pop('self')
    for name, value in d.iteritems():
        setattr(self, name, value)

def StartProcedure(procname, omsid):
    """Start a procedure
    
    procname is the name that will appear in the Viewer outline.  It may be translated
    omsid is the OMS procedure identifier and should not be translated.
    
    Statistics versions prior to 19 support only a single term used for both purposes.
    For those versions, the omsid will be use for the procedure name.
    
    While the spss.StartProcedure function accepts the one argument, this function
    requires both."""
    
    try:
        spss.StartProcedure(procname, omsid)
    except TypeError:  #older version
        spss.StartProcedure(omsid)