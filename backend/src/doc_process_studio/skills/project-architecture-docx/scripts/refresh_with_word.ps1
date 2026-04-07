param(
    [Parameter(Mandatory = $true)]
    [string]$DocumentPath
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $DocumentPath)) {
    throw "文档不存在: $DocumentPath"
}

$word = $null
$document = $null

try {
    function Set-RangeFontFinal($range, [double]$size) {
        $range.Font.Name = "Times New Roman"
        $range.Font.NameAscii = "Times New Roman"
        $range.Font.NameFarEast = "宋体"
        $range.Font.NameBi = "Times New Roman"
        $range.Font.Size = $size
    }

    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0

    $document = $word.Documents.Open($DocumentPath, $false, $false)

    foreach ($styleName in @("toc 1", "toc 2", "toc 3")) {
        try {
            $style = $document.Styles.Item($styleName)
            $style.Font.Name = "Times New Roman"
            $style.Font.NameAscii = "Times New Roman"
            $style.Font.NameFarEast = "宋体"
            $style.Font.NameBi = "Times New Roman"
            $style.Font.Size = 12
            $style.ParagraphFormat.RightIndent = 0
            $style.ParagraphFormat.CharacterUnitRightIndent = 0
        } catch {
        }
    }

    foreach ($section in $document.Sections) {
        foreach ($footerType in 1, 2, 3) {
            try {
                $footer = $section.Footers.Item($footerType)
                $footer.Range.Fields.Update() | Out-Null
                Set-RangeFontFinal $footer.Range 10
            } catch {
            }
        }
        foreach ($headerType in 1, 2, 3) {
            try {
                $section.Headers.Item($headerType).Range.Fields.Update() | Out-Null
            } catch {
            }
        }
    }

    $document.TablesOfContents | ForEach-Object { $_.Update() }
    $document.Fields.Update() | Out-Null
    $document.Repaginate()
    $document.TablesOfContents | ForEach-Object { $_.Update() }
    $document.Fields.Update() | Out-Null

    foreach ($paragraph in $document.Paragraphs) {
        try {
            $text = $paragraph.Range.Text.Trim([char]13, [char]7, ' ')
            if ($text -eq "文檔修訂曆史") {
                $nextRange = $paragraph.Range.Duplicate
                $nextRange.Collapse(0)
                if ($nextRange.Tables.Count -gt 0) {
                    $table = $nextRange.Tables.Item(1)
                    Set-RangeFontFinal $table.Range 10
                }
            }
        } catch {
        }
    }

    foreach ($paragraph in $document.Paragraphs) {
        try {
            $styleName = $paragraph.Range.Style.NameLocal
            if ($styleName -in @("toc 1", "toc 2", "toc 3")) {
                Set-RangeFontFinal $paragraph.Range 12
                $paragraph.Format.RightIndent = 0
                $paragraph.Format.CharacterUnitRightIndent = 0
            }
        } catch {
        }
    }

    $document.Save()
    Write-Output "WORD_REFRESH_OK"
} finally {
    if ($document -ne $null) {
        $document.Close([ref]$false)
    }
    if ($word -ne $null) {
        $word.Quit()
    }
}
