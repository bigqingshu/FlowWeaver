using System.Text.Json;
using Avalonia_UI.Models;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class DataPreviewWorkbenchGridStateTests
{
    [TestMethod]
    public void TryUpdateCell_UpdatesValidCellAndMarksStateDirty()
    {
        var state = CreateState();

        var updated = state.TryUpdateCell(0, 1, "changed");

        Assert.IsTrue(updated);
        Assert.AreEqual("changed", state.EditableCellRows[0][1]);
        Assert.IsTrue(state.IsDirty);
    }

    [TestMethod]
    public void TryUpdateCell_RejectsSameValueAndInvalidIndexes()
    {
        var state = CreateState();

        Assert.IsFalse(state.TryUpdateCell(0, 0, "first"));
        Assert.IsFalse(state.TryUpdateCell(-1, 0, "changed"));
        Assert.IsFalse(state.TryUpdateCell(0, 2, "changed"));
        Assert.IsFalse(state.IsDirty);
    }

    [TestMethod]
    public void TextInputAndGridStateNormalizeNullCellValue()
    {
        var state = CreateState();
        string? updatedValue = null;
        var input = new TableDataPreviewCellViewModel(
            "second",
            value =>
            {
                updatedValue = value;
                state.TryUpdateCell(0, 1, value);
            });

        input.Text = null;

        Assert.AreEqual(string.Empty, input.Text);
        Assert.AreEqual(string.Empty, updatedValue);
        Assert.AreEqual(string.Empty, state.EditableCellRows[0][1]);
        Assert.IsTrue(state.IsDirty);
    }

    [TestMethod]
    public void RestoreEditableRows_ReturnsCleanIndependentCopy()
    {
        var state = CreateState();
        state.TryUpdateCell(0, 1, "changed");

        var restored = state.RestoreEditableRows();

        Assert.IsFalse(restored.IsDirty);
        Assert.AreEqual("second", restored.EditableCellRows[0][1]);
        Assert.AreNotSame(
            restored.OriginalCellRows[0],
            restored.EditableCellRows[0]);
    }

    [TestMethod]
    public void PagingState_UsesLoadedOffsetAndRowCount()
    {
        var state = CreateState(offset: 20, hasMore: true, rowCount: 42);

        Assert.IsTrue(state.HasPreviousPage);
        Assert.IsTrue(state.HasMore);
        Assert.HasCount(1, state.Rows);
        Assert.AreEqual(21, state.FirstVisibleRowNumber);
        Assert.AreEqual(21, state.LastVisibleRowNumber);
        Assert.AreEqual(10, state.GetPreviousPageOffset(pageSize: 10));
        Assert.AreEqual(30, state.GetNextPageOffset(pageSize: 10));
    }

    [TestMethod]
    public void PagingState_ClampsPreviousOffsetAtZero()
    {
        var state = CreateState(offset: 5);

        Assert.AreEqual(0, state.GetPreviousPageOffset(pageSize: 10));
    }

    private static DataPreviewWorkbenchGridState CreateState(
        int offset = 0,
        bool hasMore = false,
        long rowCount = 1)
    {
        var originalCellRows = new[]
        {
            new[] { "first", "second" },
        };
        return new DataPreviewWorkbenchGridState
        {
            Columns = ["a", "b"],
            Rows = [JsonSerializer.SerializeToElement(new { a = "first", b = "second" })],
            OriginalCellRows = originalCellRows,
            EditableCellRows = DataPreviewTableGridBuilder.CloneCellRows(
                originalCellRows),
            Offset = offset,
            HasMore = hasMore,
            RowCount = rowCount,
        };
    }
}
