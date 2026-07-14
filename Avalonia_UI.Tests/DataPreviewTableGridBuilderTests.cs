using System.Text.Json;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class DataPreviewTableGridBuilderTests
{
    [TestMethod]
    public void BuildGridFormatsJsonRowsForPreviewCells()
    {
        var rows = TableRows(
            ["id", "name", "active", "missing", "empty"],
            [
                JsonDocument.Parse(
                        """{"id":1,"name":"Alice","active":true,"empty":null}""")
                    .RootElement
                    .Clone(),
            ]);

        var grid = DataPreviewTableGridBuilder.BuildGrid(rows);

        CollectionAssert.AreEqual(
            new[] { "id", "name", "active", "missing", "empty" },
            grid.Columns);
        CollectionAssert.AreEqual(
            new[] { "1", "Alice", "true", string.Empty, string.Empty },
            grid.CellRows[0]);
    }

    [TestMethod]
    public void BuildWorkbenchStateClonesRowsAndCellRows()
    {
        var rows = TableRows(
            ["name", "amount"],
            [
                JsonDocument.Parse("""{"name":"Alice","amount":12}""")
                    .RootElement
                    .Clone(),
            ],
            rowCount: 10,
            offset: 5,
            hasMore: true);

        var state = DataPreviewTableGridBuilder.BuildWorkbenchState(rows);
        state.EditableCellRows[0][1] = "99";

        Assert.AreEqual(5, state.Offset);
        Assert.IsTrue(state.HasMore);
        Assert.AreEqual(10, state.RowCount);
        CollectionAssert.AreEqual(new[] { "Alice", "12" }, state.OriginalCellRows[0]);
        CollectionAssert.AreEqual(new[] { "Alice", "99" }, state.EditableCellRows[0]);
        Assert.IsFalse(
            DataPreviewTableGridBuilder.CellRowsEqual(
                state.OriginalCellRows,
                state.EditableCellRows));
    }

    [TestMethod]
    public void GetVisibleRowIndexesFiltersCaseInsensitively()
    {
        string[][] rows =
        [
            ["1", "Alice"],
            ["2", "Bob"],
            ["3", "Bobby"],
        ];

        CollectionAssert.AreEqual(
            new[] { 0, 1, 2 },
            DataPreviewTableGridBuilder.GetVisibleRowIndexes(rows, " "));
        CollectionAssert.AreEqual(
            new[] { 0, 1, 2 },
            DataPreviewTableGridBuilder.GetVisibleRowIndexes(rows, null!));
        CollectionAssert.AreEqual(
            new[] { 1, 2 },
            DataPreviewTableGridBuilder.GetVisibleRowIndexes(rows, "bob"));
    }

    [TestMethod]
    public void BuildTsvEscapesTabsAndLineBreaks()
    {
        var tsv = DataPreviewTableGridBuilder.BuildTsv(
            ["name", "note"],
            [
                ["Alice", "line1\nline2"],
                ["Bob\tJr", "ok"],
                [null!, "empty"],
            ]);

        Assert.AreEqual(
            "name\tnote\nAlice\tline1 line2\nBob Jr\tok\n\tempty",
            tsv.Replace("\r\n", "\n"));
    }

    [TestMethod]
    public void TryParseDelimitedTableParsesQuotedCsvAndNormalizesHeaders()
    {
        var parsed = DataPreviewTableGridBuilder.TryParseDelimitedTable(
            "name,note,name\nAlice,\"a,b\",A2",
            out var columns,
            out var rows,
            out var errorMessage);

        Assert.IsTrue(parsed);
        Assert.IsNull(errorMessage);
        CollectionAssert.AreEqual(new[] { "name", "note", "name_2" }, columns);
        Assert.AreEqual("Alice", rows[0].GetProperty("name").GetString());
        Assert.AreEqual("a,b", rows[0].GetProperty("note").GetString());
        Assert.AreEqual("A2", rows[0].GetProperty("name_2").GetString());
    }

    [TestMethod]
    public void TryParseDelimitedTableRejectsHeaderOnlyInput()
    {
        var parsed = DataPreviewTableGridBuilder.TryParseDelimitedTable(
            "name\tamount",
            out var columns,
            out var rows,
            out var errorMessage);

        Assert.IsFalse(parsed);
        Assert.IsEmpty(columns);
        Assert.IsEmpty(rows);
        Assert.AreEqual("data_preview.paste_requires_rows", errorMessage);
    }

    [TestMethod]
    public void TryParseDelimitedTableRejectsNullInputWithoutThrowing()
    {
        var parsed = DataPreviewTableGridBuilder.TryParseDelimitedTable(
            null,
            out var columns,
            out var rows,
            out var errorMessage);

        Assert.IsFalse(parsed);
        Assert.IsEmpty(columns);
        Assert.IsEmpty(rows);
        Assert.AreEqual("data_preview.paste_requires_rows", errorMessage);
    }

    private static TableDataRowsDto TableRows(
        string[] columns,
        JsonElement[] rows,
        long? rowCount = null,
        int offset = 0,
        bool hasMore = false)
    {
        return new TableDataRowsDto
        {
            TableRefId = "table-1",
            Offset = offset,
            Limit = 50,
            RowCount = rowCount ?? rows.Length,
            Columns = columns,
            Rows = rows,
            HasMore = hasMore,
        };
    }
}
