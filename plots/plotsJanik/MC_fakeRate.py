#!/usr/bin/env python
''' Analysis script for standard plots
'''
#
# Standard imports and batch mode
#
import ROOT, os
ROOT.gROOT.SetBatch(True)
#from math                                import sqrt, cos, sin, pi, atan2, cosh

# RootTools
from RootTools.core.standard             import *

# tWZ
from tWZ.Tools.user                      import plot_directory, HistogramsForFakeStudies
from tWZ.Tools.helpers                   import getObjDict, getVarValue

# Analysis
from Analysis.Tools.helpers              import deltaPhi, deltaR
#from Analysis.Tools.puProfileCache       import *
# from Analysis.Tools.puReweighting        import getReweightingFunction
from Analysis.Tools.puReweighting        import getNVTXReweightingFunction
import Analysis.Tools.syncer

import array

# Arguments
import argparse
argParser = argparse.ArgumentParser(description = "Argument parser")
argParser.add_argument('--logLevel',       action='store',      default='INFO', nargs='?', choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'TRACE', 'NOTSET'], help="Log level for logging")
#argParser.add_argument('--noData',         action='store_true', default=False, help='also plot data?')
argParser.add_argument('--small',                             action='store_true', help='Run only on a small subset of the data?', )
#argParser.add_argument('--sorting',                           action='store', default=None, choices=[None, "forDYMB"],  help='Sort histos?', )
#argParser.add_argument('--dataMCScaling',  action='store_true', help='Data MC scaling?', )
argParser.add_argument('--plot_directory', action='store', default='tWZ_fakes')
argParser.add_argument('--era',            action='store', type=str, default="Run2016")
argParser.add_argument('--createNVtxhist',            action='store_true')
argParser.add_argument('--mode',           action='store', type=str, default="mu", choices=["mu","ele"])

#argParser.add_argument('--selection',      action='store', default='trilep-minDLmass12-onZ1-njet4p-btag2p')
args = argParser.parse_args()

# Logger
import tWZ.Tools.logger as logger
import RootTools.core.logger as logger_rt
logger    = logger.get_logger(   args.logLevel, logFile = None)
logger_rt = logger_rt.get_logger(args.logLevel, logFile = None)

if args.small:                        args.plot_directory += "_small"
#if args.noData:                       args.plot_directory += "_noData"  

logger.info( "Working in era %s", args.era)

if args.era == "Run2016":
    import tWZ.samples.nanoTuples_fakes_2016_nanoAODv6_private_postProcessed as samples

    triggers    = ["HLT_Mu3_PFJet40" ]#, "HLT_Mu8", "HLT_Mu17"]#, "HLT_Mu27"] HLT_Mu27 is actually in SingleMuon!

    data_sample = samples.DoubleMuon_Run2016
  
    mc = [samples.QCD_mu, samples.WJetsToLNu_mu, samples.TTbar_mu]
    QCD = samples.QCD_mu


triggerSelection = '('+"||".join(triggers)+')'
leptonSelection  = 'nmu_looseHybridIso==1'
jetSelection     = 'Sum$(Jet_pt>40&&abs(Jet_eta)<2.4&&JetGood_cleaned_mu_looseHybridIso)>=1'

#lumi_scale                 = data_sample.lumi/1000
# data_sample.scale          = 1.
#for sample in mc:
#    sample.scale           = 1 # Scale MCs individually with lumi

if args.small:
    for sample in [data_sample] + mc :
        sample.normalization = 1.
        sample.reduceFiles( to=3)
        #sample.scale /= sample.normalization

# Text on the plots
tex = ROOT.TLatex()
tex.SetNDC()
tex.SetTextSize(0.04)
tex.SetTextAlign(11) # align right

def drawObjects():
    lines = [
      (0.15, 0.95, 'CMS Preliminary'), 
      #(0.45, 0.95, 'L=%3.1f fb{}^{-1} (13 TeV) Scale %3.2f'% ( lumi_scale, dataMCScale ) ) if plotData else (0.45, 0.95, 'L=%3.1f fb{}^{-1} (13 TeV)' % lumi_scale)
    ]
    return [tex.DrawLatex(*l) for l in lines] 

def drawPlots(plots):
  for log in [False, True]:
    plot_directory_ = os.path.join(plot_directory, 'analysisPlots', args.plot_directory, args.era, ("log" if log else "lin"))
    for plot in plots:
      if log and plot.name=="nVtxs" and args.createNVtxhist :
        FFile = ROOT.TFile("{}/nVertexReweight.root".format(HistogramsForFakeStudies),"RECREATE")
        for h in plot.histos :
          for hh in h :
            hh.Write("_".join(hh.GetName().split("_")[:2]))
        FFile.Close()


      if not max(l.GetMaximum() for l in sum(plot.histos,[])): continue # Empty plot

      _drawObjects = []

      if isinstance( plot, Plot):
          plotting.draw(plot,
            plot_directory = plot_directory_,
            ratio = {},#{'histos':[(1,0)], 'logY':False, 'style':None, 'texY': 'Data / MC', 'yRange': (0.5, 1.5), 'drawObjects': []},#{'yRange':(0.1,1.9)} if not args.noData else None,
            logX = False, logY = log, sorting = True,
            yRange = (0.03, "auto") if log else (0.001, "auto"),
            scaling = {0:1},
            legend = ( (0.18,0.88-0.03*sum(map(len, plot.histos)),0.9,0.88), 2),
            drawObjects = drawObjects() + _drawObjects,
            copyIndexPHP = False, 
            extensions = ["png","pdf"],
            )
            
# Read variables and sequences

read_variables = [
    "weight/F",
#    "Muon[pt/F,eta/F,phi/F,dxy/F,dz/F,ip3d/F,sip3d/F,jetRelIso/F,miniPFRelIso_all/F,pfRelIso03_all/F,mvaTOP/F,mvaTTH/F,pdgId/I,segmentComp/F,nStations/I,nTrackerLayers/I]",
#    "Electron[pt/F,eta/F,phi/F,dxy/F,dz/F,ip3d/F,sip3d/F,jetRelIso/F,miniPFRelIso_all/F,pfRelIso03_all/F,mvaTOP/F,mvaTTH/F,pdgId/I,vidNestedWPBitmap/I]",
    ]

sequence       = []

read_variables += ["n%s_looseHybridIso/I"%args.mode, "%s_looseHybridIso[pt/F,eta/F,phi/F,mT/F,hybridIso/F]"%args.mode, "met_pt/F"]

def makeLeptons( event, sample ):
    collVars = ["pt","eta","phi","mT","hybridIso"]
    lep  = getObjDict(event, args.mode+'_looseHybridIso_', collVars, 0)
    for var in collVars:
        setattr( event, "lep_"+var, lep[var]  )
    

sequence.append( makeLeptons )

allPlots   = {}

data_sample.texName = "data"
data_sample.name    = "data"
data_sample.style   = styles.errorStyle(ROOT.kBlack)
#lumi_scale          = data_sample.lumi/1000

if args.createNVtxhist == False :
  VertexReweightFile = ROOT.TFile("{}/nVertexReweight.root".format(HistogramsForFakeStudies))
  
  nVtxWeightHisto = VertexReweightFile.Get("nVtxWeightCalc")
  


for sample in mc : 
  sample.style = styles.fillStyle(sample.color)
  if args.createNVtxhist == False :
    sample.weight = lambda event, sample: nVtxWeightHisto.GetBinContent(nVtxWeightHisto.GetXaxis().FindBin(event.PV_npvsGood))
for sample in mc + [data_sample] :
  sample.setSelectionString("&&".join( [ triggerSelection, leptonSelection, jetSelection]))

stack = Stack(mc, [data_sample])




weight_ = lambda event, sample: event.weight 
# Use some defaults
Plot.setDefaults(stack = stack, weight = staticmethod(weight_))

plots = []

plots.append(Plot(
  name = 'nVtxs', texX = 'vertex multiplicity', texY = 'Number of Events',
  attribute = TreeVariable.fromString( "PV_npvsGood/I" ),
  binning=[50,0,50],
  addOverFlowBin='upper'
))
plots.append(Plot(
  name = 'met_pt', texX = 'MET', texY = 'Number of Events',
  attribute = TreeVariable.fromString( "met_pt/F" ),
  binning=[50,0,250],
  addOverFlowBin='upper',
))


plots.append(Plot(
  name = args.mode+'_pt', texX = 'p_{T}', texY = 'Number of Events',
  attribute = lambda event, sample: event.lep_pt,
  binning=[100,0,50],
  addOverFlowBin='upper',
))

plots.append(Plot(
  name = args.mode+'_eta', texX = '#eta', texY = 'Number of Events',
  attribute = lambda event, sample: event.lep_eta,
  binning=[30,-3,3],
  addOverFlowBin='upper',
))

plots.append(Plot(
  name = args.mode+'_mT', texX = 'm_{T}', texY = 'Number of Events',
  attribute = lambda event, sample: event.lep_mT,
  binning=[40,0,200],
  addOverFlowBin='upper',
))

plots.append(Plot(
  name = args.mode+'_hybridIso_lowpT', texX = 'hybridIso (lowPt)', texY = 'Number of Events',
  attribute = lambda event, sample: event.lep_hybridIso if event.lep_pt<25 else float('nan'),
  binning=[40,0,20],
  addOverFlowBin='none',
))

plots.append(Plot(
  name = args.mode+'_hybridIso_highpT', texX = 'hybridIso (highPt)', texY = 'Number of Events',
  attribute = lambda event, sample: event.lep_hybridIso if event.lep_pt>25 else float('nan'),
  binning=[40,0,20],
  addOverFlowBin='none',
))

plotting.fill(plots, read_variables = read_variables, sequence = sequence)

drawPlots(plots)


if args.createNVtxhist :
  os.system("python {}/calc_nVtx_reweight.py".format(os.getcwd()))
else :
  VertexReweightFile.Close()
