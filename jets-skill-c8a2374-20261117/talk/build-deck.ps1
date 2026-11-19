param(
    [Parameter(Mandatory)] [string]$OutputName,
    [string]$TimingFile
)
$ErrorActionPreference = 'Stop'
if ($OutputName -notmatch '^[A-Za-z0-9._-]+\.pptx$') { throw 'Supply a new PowerPoint filename.' }
$talk = $PSScriptRoot
$report = Split-Path -Parent $talk
$target = Join-Path $talk $OutputName
if (Test-Path -LiteralPath $target) { throw "The deck already exists: $target" }
$export = Join-Path $talk ('render-' + [IO.Path]::GetFileNameWithoutExtension($OutputName))
if (Test-Path -LiteralPath $export) { throw "The render directory already exists: $export" }
$app = New-Object -ComObject PowerPoint.Application
$before = $app.Presentations.Count
$deck = $app.Presentations.Add(0)
function Color([string]$hex) {
    $v = [Convert]::ToInt32($hex, 16)
    return (($v -band 255) -shl 16) -bor ($v -band 65280) -bor (($v -shr 16) -band 255)
}
$blue = Color '28678A'
$orange = Color 'A44420'
$ink = Color '25343C'
function Label($s, $text, $x, $y, $w, $h, $size=22, $color=$ink, $font='Calibri') {
    $shape = $s.Shapes.AddTextbox(1, $x, $y, $w, $h)
    $shape.TextFrame.MarginLeft = 0
    $shape.TextFrame.MarginRight = 0
    $shape.TextFrame.MarginTop = 0
    $shape.TextFrame.WordWrap = -1
    $shape.TextFrame.TextRange.Text = $text
    $shape.TextFrame.TextRange.Font.Name = $font
    $shape.TextFrame.TextRange.Font.Size = $size
    $shape.TextFrame.TextRange.Font.Color.RGB = $color
    $shape.TextFrame.TextRange.ParagraphFormat.SpaceAfter = 6
    return $shape
}
function Slide($title, $notes) {
    $s = $deck.Slides.Add($deck.Slides.Count + 1, 11)
    $t = $s.Shapes.Title
    $t.Left = 43
    $t.Top = 21
    $t.Width = 878
    $t.Height = 61
    $t.TextFrame.TextRange.Text = $title
    $t.TextFrame.TextRange.Font.Name = 'Calibri Light'
    $t.TextFrame.TextRange.Font.Size = 36
    $t.TextFrame.TextRange.Font.Color.RGB = $ink
    $s.NotesPage.Shapes.Placeholders.Item(2).TextFrame.TextRange.Text = $notes
    $s.HeadersFooters.Footer.Visible = -1
    $s.HeadersFooters.Footer.Text = 'Gordon Watts (UW/Seattle)'
    $s.HeadersFooters.SlideNumber.Visible = -1
    return $s
}
function Table($s, $rows, $x, $y, $width, $height, $fontSize=20) {
    $columns = $rows[0].Count
    $table = $s.Shapes.AddTable($rows.Count, $columns, $x, $y, $width, $height).Table
    for ($r = 1; $r -le $rows.Count; $r++) {
        for ($c = 1; $c -le $columns; $c++) {
            $shape = $table.Cell($r,$c).Shape
            $shape.TextFrame.TextRange.Text = [string]$rows[$r-1][$c-1]
            $shape.TextFrame.TextRange.Font.Name = 'Calibri'
            $shape.TextFrame.TextRange.Font.Size = $fontSize
            $shape.TextFrame.TextRange.Font.Bold = [int]($r -eq 1) * -1
            $shape.Fill.ForeColor.RGB = $(if ($r -eq 1) { $blue } elseif ($r % 2 -eq 0) { Color 'F0F5F7' } else { Color 'FFFFFF' })
            $shape.TextFrame.TextRange.Font.Color.RGB = $(if ($r -eq 1) { Color 'FFFFFF' } else { $ink })
        }
    }
}
function Figure($s, $file, $x, $y, $width, $height) {
    $p = $s.Shapes.AddPicture((Join-Path $report "figures/$file"), 0, -1, $x, $y, -1, -1)
    $scale = [Math]::Min($width / $p.Width, $height / $p.Height)
    $p.LockAspectRatio = -1
    $p.Width *= $scale
    $p.Left = $x + ($width - $p.Width)/2
    $p.Top = $y + ($height - $p.Height)/2
}
function Arrow($s,$x1,$y1,$x2,$y2) {
    $a = $s.Shapes.AddLine($x1,$y1,$x2,$y2)
    $a.Line.ForeColor.RGB = $blue
    $a.Line.Weight = 1.8
    $a.Line.EndArrowheadStyle = 3
}
try {
    $deck.PageSetup.SlideWidth = 960
    $deck.PageSetup.SlideHeight = 540
    $deck.SlideMaster.Theme.ThemeFontScheme.MajorFont.Item(1).Name = 'Calibri Light'
    $deck.SlideMaster.Theme.ThemeFontScheme.MinorFont.Item(1).Name = 'Calibri'
    $deck.SlideMaster.HeadersFooters.Footer.Text = 'Gordon Watts (UW/Seattle)'
    $deck.SlideMaster.HeadersFooters.Footer.Visible = -1
    $deck.SlideMaster.HeadersFooters.SlideNumber.Visible = -1
    $s = Slide 'Can Both Jet Sizes Use the Same Calibration Code?' 'S001. The question is practical. An analysis often needs both collections. Where does a shared calculation preserve the release prescription, and when does it save time?'
    $s.Shapes.Title.Top = 112
    $s.Shapes.Title.Height = 110
    $s.Shapes.Title.TextFrame.TextRange.Font.Size = 44
    $null = Label $s 'Small-R and large-R jet calibration from Run 3 PHYSLITE' 49 275 850 65 28 $blue
    $null = Label $s 'AnalysisBase 25.2.117  ·  20,000 simulated top-pair events' 49 349 850 50 21

    $s = Slide 'Two Collections in the Same Events' 'S002. The event and object indices stay fixed, including 6,533 events with no large-R jet. The release registered 331 distinct states. The common names include the up and down flavour composition, flavour response and vertexing JES variations. Source: evidence/reference/jet-states.json.'
    Table $s @(@('','Small-R','Large-R'),@('Input','R = 0.4 particle flow','R = 1.0 UFO soft drop'),@('Original jets','196,606','22,177'),@('Configured states','119, including 2 weight-only','219, including 36 JMR'),@('Histogram','All jets, with NNJVT weight','Selected jets, unit weight')) 47 97 868 255 18
    $null = Label $s 'Both collections use category JES and full JER. Large-R also varies mass scale and mass resolution.' 48 383 862 76 23

    $s = Slide 'Three Paths From PHYSLITE to the Histogram' 'S003. A supplies independent numerical authority. B keeps the analysis configuration and replaces numerical bodies. C reads the original branches with uproot. In timing, A and B write analysis ntuples, then a separate process reads them and writes the histogram. The C endpoint includes reading the input and saving the histogram.'
    Table $s @(@('Path','Calculation','Output path'),@('A · AnalysisBase','Original CP tools','Ntuple → histogram'),@('B · AnalysisBase','Converted CorrectionLib nodes','Ntuple → histogram'),@('C · Python','Same converted numerical bodies','Direct histogram')) 47 103 865 250 20
    $null = Label $s 'One execution thread on one assigned CPU. Compare each replacement independently with A.' 48 386 840 74 22 $blue

    $s = Slide 'Where the Two Jet Recipes Meet' 'S004. Read from left to right. EtaJES uses the same calibration class with collection-dependent coefficients. The common uncertainty implementation binds the initialized groups and tables for the requested jet definition. JVT and forward folding have genuinely different physics. B and C use these same numerical implementations.'
    $null = Label $s 'Small-R' 42 110 118 38 24 $orange
    $null = Label $s 'Large-R' 42 294 118 38 24 $orange
    $null = Label $s 'Pile-up and residual' 160 93 128 84 19
    $null = Label $s 'Constituent scale' 160 285 120 67 19
    $null = Label $s 'EtaJES' 307 192 92 42 24 $blue
    $null = Label $s 'Global sequential correction' 433 89 170 91 19
    $null = Label $s 'Mass calibration' 433 288 160 75 19
    $null = Label $s 'Jet uncertainty groups' 622 177 135 98 21 $blue
    $null = Label $s 'NNJVT score, selection, weights' 790 87 152 100 19
    $null = Label $s 'Mass resolution and selection' 790 281 151 94 19
    Arrow $s 272 130 304 192
    Arrow $s 270 295 303 224
    Arrow $s 393 203 427 141
    Arrow $s 393 213 427 299
    Arrow $s 582 133 617 185
    Arrow $s 575 312 617 233
    Arrow $s 747 186 785 135
    Arrow $s 747 232 785 300
    $null = Label $s 'Shared nodes use the coefficients and state inventory for the selected jet definition.' 48 407 863 59 22

    $s = Slide 'How Python Calls the Shared Calculation' 'The visible script first loads the explicit provider and reads the CorrectionSet. In the chunk loop, corrected.T supplies the four coordinate columns and detector_eta supplies the detector pseudorapidity of each jet. The two named EtaJES corrections bind the same registered native implementation to their respective constants. The value returned is the corrected four-vector in release units. These excerpts are from load_corrections and evaluate_chunk. The intervening code is omitted.'
    $null = Label $s 'Load the native nodes and their calibration data' 48 103 862 40 21 $blue
    $null = Label $s "plugins.load_library(str(resolved))`nnodes = CorrectionSet.from_file(str(payload))" 48 158 862 85 21 $ink 'Consolas'
    $null = Label $s 'Choose the calibrated response for this jet radius' 48 280 862 40 21 $blue
    $null = Label $s "corrected = nodes[`n    `"small_eta_jes`" if prefix == `"sr`" else `"large_eta_jes`"`n].evaluate(*corrected.T, detector_eta)" 48 337 870 125 20 $ink 'Consolas'

    $s = Slide 'The First Jet Identified a Wrong Input' 'S005. Entry zero, jet zero. Both candidate branches exist and both contain floats. The release explicitly configured the neutral particle-flow energy density. With a jet area of about 0.488, the density difference accounts for the observed 604 MeV pT difference. Source: small-source.md and evidence/validation/direct-100/comparison.json.'
    Table $s @(@('Input density','First event'),@('Inclusive particle flow','8,595.822 MeV'),@('Neutral particle flow','7,358.803 MeV')) 50 104 850 173 22
    $null = Label $s 'A 604 MeV difference appeared immediately after small-R pile-up subtraction.' 51 319 820 83 28 $orange
    $null = Label $s 'Selecting the release-configured neutral density restored agreement.' 51 418 825 58 21

    $s = Slide 'What the Two Analyses Histogram' 'S006. Upper panels are independent saved histogram bins. Lower panels show direct minus stock. The physics endpoint also checks entries, flows, sum of weights and sum of squared weights for all applicable states. 3,302 large-R jets pass the nominal selection. Source: evidence/histograms/histogram-comparison.json.'
    Figure $s 'nominal-pt.png' 42 74 874 394
    $null = Label $s 'Every saved bin agrees for 119 small-R and 219 large-R states.' 52 475 842 38 19 $blue

    $s = Slide 'Seven Input Leaves Are Shared' 'S007. The sample contains 20,000 original entries. The seven shared leaves represent 7.62 MB of compressed ROOT baskets, or 17.1% of the summed input. The joint standalone job took 12.832 s versus 14.178 s for the two separate runs. The converted framework took 277.32 s jointly versus 249.34 s separately. Its combined output persists the union of 353 and 657 branches. The stock comparison showed the same direction with excess scatter in the combined sample. Basket bytes count the serialized representation. Actual storage traffic depends on caching. Sources: timing-results.md, evidence/diagnostics/footprint.json and evidence/diagnostics/joint-framework-scope.json.'
    Table $s @(@('Full workflow','Distinct ROOT leaves','Compressed input'),@('Small-R','26','34.14 MB'),@('Large-R','21','10.55 MB'),@('One combined read','40','37.07 MB')) 48 112 856 220 22
    $null = Label $s 'Direct Python took 12.83 s together versus 14.18 s separately, saving 9.5%. The converted framework took 11.2% longer together.' 49 355 855 117 23 $blue

    $s = Slide 'Which Part of the Calculation Costs Time?' 'S008. One instrumented diagnostic on the first 2,000 events, with each collection in the same job. The original-boundary provider constructed release jet and event objects for uncertainty evaluation. The portable model evaluates the same configured groups directly on the jet coordinates. These are call-boundary wall measurements, including the binding. Source: evidence/diagnostics/phase-001.'
    Table $s @(@('Both collections, 2,000 events','Release-backed nodes','Portable nodes'),@('Provider and payload load','3.770 s','3.247 s'),@('Small-R uncertainties','4.551 s','1.034 s'),@('Large-R uncertainties','0.637 s','0.088 s'),@('Small-R NNJVT update','0.308 s','0.295 s')) 47 99 869 243 19
    $null = Label $s 'The shared uncertainty implementation handles 2.33 million small-R and 0.40 million large-R requests in this sample.' 49 380 844 79 22

    $s = Slide 'Millions of Requests Reuse the Same Random Draw' 'S008a. Both radii use a deterministic original seed derived from the jet azimuth. An exact cache stores the first unscaled Gaussian. The four negative small-R factors restarted from the original seed and took the release rejection path. The table gives the first accepted one-mebibyte implementation. Three retained full-file jobs went into each mean. The large-R-only timing spread exceeded the limit. Source: evidence/timing/engineering/original-stream-pairs.json and evidence/diagnostics/cache-use.'
    Table $s @(@('Full file','Without cache','Original-stream cache'),@('Small-R','20.76 s','17.24 s'),@('Both collections','23.09 s','18.73 s')) 47 98 868 202 22
    $null = Label $s 'Reuse the first standard Gaussian, then apply the width for each state. The original rejection sequence still runs if the first factor is negative.' 49 328 850 121 24 $blue

    $s = Slide 'Only Changed Small-R Inputs Need Another Network Call' 'S008b. The Python adapter compares the bits of the network kinematics with nominal within the owned input chunk. The features are fixed for the original jet in that chunk. Unchanged rows reuse the raw nominal NNJVT update. Other rows call the usual registered native network again. Selection, SF direction, validity and the event product run in the original order. The three retained observations passed both spread gates. Source: evidence/timing/engineering/original-stream-pairs.json.'
    Table $s @(@('With the Gaussian cache','Evaluate each update','Reuse unchanged updates'),@('Small-R','17.24 s','15.71 s'),@('Both collections','18.73 s','17.69 s')) 47 98 868 202 21
    $null = Label $s 'The optimization acts on the NNJVT score. A weight variation can still change how much a jet contributes to the histogram.' 49 327 850 120 24 $blue

    $s = Slide 'One Wheel Can Load Just the Requested Radius' 'S008c. The lossless codec preserves each of 6,300,300 original binary32 EtaJES response cells. Both collections share one canonical document. For single-radius jobs the visible packaged script copies indexed byte ranges before loading. The elapsed measurements include that temporary file. The repeated result has one warm-up and three retained full-file jobs per choice. The small-R timing difference is comparable to its run-to-run spread. Source: evidence/diagnostics/eta-jes-packing.json and evidence/diagnostics/loading-repeat.'
    Table $s @(@('Single-radius job','Parse both radii','Construct selected radius'),@('Small-R','13.96 ± 0.35 s','13.57 ± 0.49 s'),@('Large-R','3.65 ± 0.05 s','3.26 ± 0.03 s')) 47 100 868 205 20
    $null = Label $s 'Packing shrank the joint JSON from 160.84 to 75.85 MB. Scoped loading also saved about 77 MiB and 87 MiB of peak memory.' 49 332 850 118 23 $blue
    if ($TimingFile) {
        $timing = Get-Content -Raw -LiteralPath $TimingFile | ConvertFrom-Json
        foreach ($entry in $timing.slides) {
            $s = Slide $entry.title $entry.notes
            if ($entry.figure) {
                Figure $s $entry.figure 39 72 881 370
                $null = Label $s $entry.takeaway 49 451 853 58 19 $blue
            } else {
                Table $s $entry.rows 47 100 866 245 19
                $null = Label $s $entry.takeaway 49 380 845 79 24 $blue
            }
        }
        $s = Slide 'Where the Installed Workflow Spends CPU Time' 'The two captures sampled user CPU while the installed workflow repeatedly reopened the same 20,000-event file. The final run recorded 10,536 in-window samples in 105.94 seconds, with zero reported losses. Each stack has one owner. Shared uncertainties account for 31.53% and the small-R neural-network update for 15.28%. Raw symbol coverage is incomplete. The figure compares sampled CPU seconds per file, and the preceding timing plot uses fresh-process wall time. Sources: profile-results.md and evidence/final/native/recording.json.'
        Figure $s 'native-processing-time.png' 38 70 884 371
        $null = Label $s 'The shared uncertainty calculation still takes the most CPU. Small-R NNJVT is the largest collection-specific cost.' 49 451 850 65 20 $blue
    }
    $s = Slide 'Run the Installed Wheel on the Original File' 'S009. The visible PEP 723 script declares its local wheel, selects physical branches, iterates chunks and states, calls the registered nodes and fills histograms. The default is a single complete pass, both collections and all configured states. The -n option repeats complete file opens and writes one final-pass result. See the local delivery manifest and the three independent stock-versus-shipped comparisons in the report.'
    $null = Label $s 'taskset -c 3 uv run --script jets_demo.py INPUT.root OUTPUT.npz' 49 119 863 65 19 $blue 'Consolas'
    $null = Label $s 'CPython 3.14  ·  Linux x86-64  ·  One input traversal' 49 211 855 57 24
    $null = Label $s 'The wheel carries the evaluator, native jet nodes, network and calibration data. The visible script reads PHYSLITE directly with uproot.' 49 300 840 115 25
    if ($TimingFile) {
        # Keep the detailed diagnosis and mechanism tables available for working-group questions.
        $backupTitles = @('The First Jet Identified a Wrong Input',
                          'Which Part of the Calculation Costs Time?',
                          'Only Changed Small-R Inputs Need Another Network Call',
                          'One Wheel Can Load Just the Requested Radius')
        foreach ($title in $backupTitles) {
            for ($i = 1; $i -le $deck.Slides.Count; $i++) {
                $slide = $deck.Slides.Item($i)
                if ($slide.Shapes.Title.TextFrame.TextRange.Text -eq $title) {
                    $slide.MoveTo($deck.Slides.Count)
                    break
                }
            }
        }
    }
    $panels = @(@('Small-R Four-Vectors','sr-coordinates.png'),@('Large-R Four-Vectors','lr-coordinates.png'),@('NNJVT Scores and Weights','sr-weights.png'))
    if (Test-Path -LiteralPath (Join-Path $report 'figures/sr-energy.png')) {
        $panels += ,@('Small-R Energy From the Four-Vector','sr-energy.png')
    }
    $panels += @(@('All Systematic States','all-state-agreement.png'),@('Representative Momentum Variations','representative-shifts.png'))
    if (Test-Path -LiteralPath (Join-Path $report 'figures/selection-validity.png')) {
        $panels += ,@('Selections and Validity Across Variations','selection-validity.png')
    }
    foreach ($fig in $panels) {
        $s = Slide $fig[0] 'Backup. Independent histograms contain all original jets before final selection. Each residual subtracts AnalysisBase from the installed direct CorrectionLib workflow. The event scale factor has one entry per event. Per-state flow, NaN, status and exact value checks are preserved in evidence/final/metadata.json and evidence/final/distributions.npz.'
        Figure $s $fig[1] 24 69 912 436
    }
    $deck.SaveAs($target, 24)
    $deck.Export($export, 'PNG', 1440, 810)
    Write-Output "$($deck.Slides.Count) slides saved in $target"
} finally {
    $deck.Close()
    if ($before -eq 0 -and $app.Presentations.Count -eq 0) { $app.Quit() }
}
