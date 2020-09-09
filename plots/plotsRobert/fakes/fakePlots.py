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
from tWZ.Tools.user                      import plot_directory, cache_dir
from tWZ.Tools.helpers                   import getObjDict, getVarValue
# Analysis
from Analysis.Tools.helpers              import deltaPhi, deltaR
from Analysis.Tools.metFilters           import getFilterCut
from Analysis.Tools.DirDB                import DirDB
import Analysis.Tools.syncer             as syncer

# Arguments
import argparse
argParser = argparse.ArgumentParser(description = "Argument parser")
argParser.add_argument('--logLevel',       action='store',      default='INFO', nargs='?', choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'TRACE', 'NOTSET'], help="Log level for logging")
#argParser.add_argument('--noData',         action='store_true', default=False, help='also plot data?')
argParser.add_argument('--small',                             action='store_true', help='Run only on a small subset of the data?', )
#argParser.add_argument('--sorting',                           action='store', default=None, choices=[None, "forDYMB"],  help='Sort histos?', )
#argParser.add_argument('--dataMCScaling',  action='store_true', help='Data MC scaling?', )
argParser.add_argument('--plot_directory', action='store', default='tWZ_fakes_v2_QCD_pt')
argParser.add_argument('--era',            action='store', type=str, default="Run2016")
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
year = int(args.era[3:]) # this is designed to fail for era "RunII"

if args.era == "Run2016":
    import tWZ.samples.nanoTuples_fakes_2016_nanoAODv6_private_postProcessed as samples
    if args.mode=='mu':
        data_sample =  samples.DoubleMuon_Run2016
        triggers    = ["HLT_Mu3_PFJet40" ]#, "HLT_Mu8", "HLT_Mu17"]#, "HLT_Mu27"] HLT_Mu27 is actually in SingleMuon!
        mc = [ samples.QCD_pt_mu, samples.WJetsToLNu_mu, samples.TTbar_mu]
    elif args.mode=='ele':
        data_sample =  samples.DoubleEG_Run2016
        triggers    = ["HLT_Ele8_CaloIdM_TrackIdM_PFJet30" ]
        mc = [ samples.QCD_pt_ele, samples.WJetsToLNu_ele, samples.TTbar_ele]

    #mc = [Summer16.TWZ_NLO_DR, Summer16.TTZ, Summer16.TTX_rare, Summer16.TZQ, Summer16.WZ, Summer16.triBoson, Summer16.ZZ, Summer16.nonprompt_3l]
#elif args.era == "Run2017":
#    mc = [Fall17.TWZ_NLO_DR, Fall17.TTZ, Fall17.TTX_rare, Fall17.TZQ, Fall17.WZ, Fall17.triBoson, Fall17.ZZ, Fall17.nonprompt_3l]
#elif args.era == "Run2018":
#    mc = [Autumn18.TWZ_NLO_DR, Autumn18.TTZ, Autumn18.TTX_rare, Autumn18.TZQ, Autumn18.WZ, Autumn18.triBoson, Autumn18.ZZ, Autumn18.nonprompt_3l]
#elif args.era == "RunII":
#    mc = [TWZ_NLO_DR, TTZ, TTX_rare, TZQ, WZ, triBoson, ZZ, nonprompt_3l]

triggerSelection = '('+"||".join(triggers)+')'
leptonSelection  = 'n%s_looseHybridIso==1'%args.mode
jetSelection     = 'Sum$(Jet_pt>40&&abs(Jet_eta)<2.4&&JetGood_cleaned_%s_looseHybridIso)>=1'%args.mode

if args.small:
    for sample in [data_sample] + mc:
        sample.normalization = 1.
        #sample.reduceFiles( factor = 10 )
        sample.reduceFiles( to=3)
        #sample.scale /= sample.normalization

# Text on the plots
tex = ROOT.TLatex()
tex.SetNDC()
tex.SetTextSize(0.04)
tex.SetTextAlign(11) # align right

# fire up the cache
cache_dir_ = os.path.join(cache_dir, 'fake_pu_cache')
dirDB      = DirDB(cache_dir_)

pu_key = ( triggerSelection, leptonSelection, jetSelection, args.era, args.small)
if dirDB.contains( pu_key ):
    reweight_histo = dirDB.get( pu_key )
    logger.info( "Found PU reweight in cache %s", cache_dir_ )
else:
    logger.info( "Didn't find PU reweight histo %r. Obtaining it now.", pu_key)

    data_selectionString = "&&".join([getFilterCut(isData=True, year=year), triggerSelection, leptonSelection, jetSelection])
    data_nvtx_histo = data_sample.get1DHistoFromDraw( "PV_npvsGood", [100/5, 0, 100], selectionString=data_selectionString, weightString = "weight" )
    data_nvtx_histo.Scale(1./data_nvtx_histo.Integral())

    mc_selectionString = "&&".join([getFilterCut(isData=False, year=year), triggerSelection, leptonSelection, jetSelection])
    mc_histos  = [ s.get1DHistoFromDraw( "PV_npvsGood", [100/5, 0, 100], selectionString=mc_selectionString, weightString = "weight*reweightBTag_SF") for s in mc]
    mc_histo     = mc_histos[0]
    for h in mc_histos[1:]:
        mc_histo.Add( h )

    mc_histo.Scale(1./mc_histo.Integral())

    reweight_histo = data_nvtx_histo.Clone()
    reweight_histo.Divide(mc_histo)
    
    dirDB.add( pu_key, reweight_histo ) 
    logger.info( "Added PU reweight to cache %s", cache_dir_ )

# define reweight
def nvtx_puRW( event, sample ):
    return reweight_histo.GetBinContent(reweight_histo.FindBin( event.PV_npvsGood ))

#lumi_scale                 = data_sample.lumi/1000
data_sample.scale   = 1.
for sample in mc:
    sample.weight   = nvtx_puRW


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
      if not max(l.GetMaximum() for l in sum(plot.histos,[])): continue # Empty plot

      _drawObjects = []

      if isinstance( plot, Plot):
          plotting.draw(plot,
            plot_directory = plot_directory_,
            #ratio = {'yRange':(0.1,1.9)} if not args.noData else None,
            logX = False, logY = log, sorting = True,
            yRange = (0.03, "auto") if log else (0.001, "auto"),
            scaling = {0:1},
            legend = ( (0.18,0.88-0.03*sum(map(len, plot.histos)),0.9,0.88), 2),
            drawObjects = drawObjects() + _drawObjects,
            copyIndexPHP = True, extensions = ["png"],
          )
            
# Read variables and sequences

read_variables = [
    "weight/F", "PV_npvsGood/I"
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


for sample in mc: sample.style = styles.fillStyle(sample.color)
for sample in mc + [data_sample]:
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
  addOverFlowBin='upper',
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
