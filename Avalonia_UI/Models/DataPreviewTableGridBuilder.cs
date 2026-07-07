using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.Json;
using Avalonia_UI.Api;

namespace Avalonia_UI.Models;

public sealed record DataPreviewTableGrid
{
    public string[] Columns { get; init; } = [];

    public string[][] CellRows { get; init; } = [];
}

public sealed record DataPreviewWorkbenchGridState
{
    public string[] Columns { get; init; } = [];

    public JsonElement[] Rows { get; init; } = [];

    public string[][] OriginalCellRows { get; init; } = [];

    public string[][] EditableCellRows { get; init; } = [];

    public int Offset { get; init; }

    public bool HasMore { get; init; }

    public long RowCount { get; init; }
}

public static class DataPreviewTableGridBuilder
{
    public static DataPreviewTableGrid BuildGrid(TableDataRowsDto rows)
    {
        var columns = rows.Columns.ToArray();
        return new DataPreviewTableGrid
        {
            Columns = columns,
            CellRows = rows.Rows.Select(row => CreateCellRow(row, columns)).ToArray(),
        };
    }

    public static DataPreviewWorkbenchGridState BuildWorkbenchState(
        TableDataRowsDto rows)
    {
        var columns = rows.Columns.ToArray();
        var clonedRows = rows.Rows.Select(row => row.Clone()).ToArray();
        var cellRows = clonedRows.Select(row => CreateCellRow(row, columns)).ToArray();

        return new DataPreviewWorkbenchGridState
        {
            Columns = columns,
            Rows = clonedRows,
            OriginalCellRows = cellRows,
            EditableCellRows = CloneCellRows(cellRows),
            Offset = rows.Offset,
            HasMore = rows.HasMore,
            RowCount = rows.RowCount,
        };
    }

    public static int[] GetVisibleRowIndexes(
        string[][] editableCellRows,
        string searchText)
    {
        var filter = NormalizeFilter(searchText);
        var rowIndexes = Enumerable.Range(0, editableCellRows.Length);
        if (filter is null)
        {
            return rowIndexes.ToArray();
        }

        return rowIndexes
            .Where(rowIndex => editableCellRows[rowIndex].Any(
                value => value.Contains(
                    filter,
                    StringComparison.OrdinalIgnoreCase)))
            .ToArray();
    }

    public static bool CellRowsEqual(string[][] left, string[][] right)
    {
        if (left.Length != right.Length)
        {
            return false;
        }

        for (var rowIndex = 0; rowIndex < left.Length; rowIndex++)
        {
            if (!left[rowIndex].SequenceEqual(right[rowIndex], StringComparer.Ordinal))
            {
                return false;
            }
        }

        return true;
    }

    public static string BuildTsv(
        IEnumerable<string> columns,
        IEnumerable<IEnumerable<string>> cellRows)
    {
        var builder = new StringBuilder();
        builder.AppendLine(string.Join("\t", columns.Select(EscapeTsv)));
        foreach (var row in cellRows)
        {
            builder.AppendLine(string.Join("\t", row.Select(EscapeTsv)));
        }

        return builder.ToString().TrimEnd('\r', '\n');
    }

    public static bool TryParseDelimitedTable(
        string text,
        out string[] columns,
        out JsonElement[] rows,
        out string? errorMessage)
    {
        columns = [];
        rows = [];
        errorMessage = null;

        var lines = text
            .Replace("\r\n", "\n", StringComparison.Ordinal)
            .Replace('\r', '\n')
            .Split('\n')
            .Where(line => !string.IsNullOrWhiteSpace(line))
            .ToArray();
        if (lines.Length < 2)
        {
            errorMessage = "data_preview.paste_requires_rows";
            return false;
        }

        var delimiter = lines[0].Contains('\t', StringComparison.Ordinal) ? '\t' : ',';
        var parsedRows = lines.Select(line => ParseDelimitedLine(line, delimiter)).ToArray();
        var maxColumnCount = parsedRows.Max(row => row.Length);
        if (maxColumnCount == 0)
        {
            errorMessage = "data_preview.paste_no_columns";
            return false;
        }

        var parsedColumns = NormalizeDelimitedHeaders(parsedRows[0], maxColumnCount);
        var parsedDataRows = parsedRows
            .Skip(1)
            .Select(row => CreateDelimitedRowElement(parsedColumns, row))
            .ToArray();
        columns = parsedColumns;
        rows = parsedDataRows;
        if (rows.Length == 0)
        {
            errorMessage = "data_preview.paste_no_rows";
            return false;
        }

        return true;
    }

    private static string[] CreateCellRow(JsonElement row, string[] columns)
    {
        return columns.Select(column => FormatCell(row, column)).ToArray();
    }

    public static string[][] CloneCellRows(string[][] rows)
    {
        return rows.Select(row => row.ToArray()).ToArray();
    }

    private static string FormatCell(JsonElement row, string column)
    {
        if (row.ValueKind != JsonValueKind.Object
            || !row.TryGetProperty(column, out var value))
        {
            return string.Empty;
        }

        return value.ValueKind switch
        {
            JsonValueKind.Null or JsonValueKind.Undefined => string.Empty,
            JsonValueKind.String => value.GetString() ?? string.Empty,
            JsonValueKind.Number or JsonValueKind.True or JsonValueKind.False =>
                value.GetRawText(),
            _ => value.GetRawText(),
        };
    }

    private static string EscapeTsv(string value)
    {
        return value
            .Replace("\r\n", " ", StringComparison.Ordinal)
            .Replace("\r", " ", StringComparison.Ordinal)
            .Replace("\n", " ", StringComparison.Ordinal)
            .Replace('\t', ' ');
    }

    private static string[] ParseDelimitedLine(string line, char delimiter)
    {
        var values = new List<string>();
        var current = new StringBuilder();
        var inQuotes = false;

        for (var index = 0; index < line.Length; index++)
        {
            var character = line[index];
            if (character == '"')
            {
                if (inQuotes && index + 1 < line.Length && line[index + 1] == '"')
                {
                    current.Append('"');
                    index++;
                    continue;
                }

                inQuotes = !inQuotes;
                continue;
            }

            if (!inQuotes && character == delimiter)
            {
                values.Add(current.ToString());
                current.Clear();
                continue;
            }

            current.Append(character);
        }

        values.Add(current.ToString());
        return values.ToArray();
    }

    private static string[] NormalizeDelimitedHeaders(string[] headerRow, int columnCount)
    {
        var headers = new string[columnCount];
        var seen = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        for (var index = 0; index < columnCount; index++)
        {
            var header = index < headerRow.Length ? headerRow[index].Trim() : string.Empty;
            if (string.IsNullOrWhiteSpace(header))
            {
                header = $"Column{index + 1}";
            }

            if (seen.TryGetValue(header, out var count))
            {
                count++;
                seen[header] = count;
                header = $"{header}_{count}";
            }
            else
            {
                seen[header] = 1;
            }

            headers[index] = header;
        }

        return headers;
    }

    private static JsonElement CreateDelimitedRowElement(string[] columns, string[] values)
    {
        var row = new Dictionary<string, string>(StringComparer.Ordinal);
        for (var index = 0; index < columns.Length; index++)
        {
            row[columns[index]] = index < values.Length ? values[index] : string.Empty;
        }

        return JsonSerializer.SerializeToElement(row, FlowWeaverJson.Options).Clone();
    }

    private static string? NormalizeFilter(string value)
    {
        var trimmed = value.Trim();
        return string.IsNullOrWhiteSpace(trimmed) ? null : trimmed;
    }
}
