using System;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void UpdateDataPreviewWorkbenchCell(
        int rowIndex,
        int columnIndex,
        string value)
    {
        if (!IsValidDataPreviewWorkbenchCellIndex(rowIndex, columnIndex))
        {
            return;
        }

        if (string.Equals(
                dataPreviewWorkbenchEditableCellRows[rowIndex][columnIndex],
                value,
                StringComparison.Ordinal))
        {
            return;
        }

        dataPreviewWorkbenchEditableCellRows[rowIndex][columnIndex] = value;
        DataPreviewWorkbenchClipboardText = string.Empty;
        NotifyDataPreviewWorkbenchDirtyStateChanged();
    }

    private bool IsValidDataPreviewWorkbenchCellIndex(int rowIndex, int columnIndex)
    {
        return rowIndex >= 0
            && rowIndex < dataPreviewWorkbenchEditableCellRows.Length
            && columnIndex >= 0
            && columnIndex < dataPreviewWorkbenchEditableCellRows[rowIndex].Length;
    }
}
