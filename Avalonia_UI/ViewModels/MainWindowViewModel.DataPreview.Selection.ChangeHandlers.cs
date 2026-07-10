using System;
using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnSelectedDataPreviewStateChanged(DataPreviewStateListItemViewModel? value)
    {
        var previousTableRefId = SelectedDataPreviewTableOption?.TableRefId;
        DataPreviewTableOptions.Clear();
        if (value is not null)
        {
            foreach (var tableRef in value.TableRefs.Where(tableRef => tableRef.CanReadRows))
            {
                DataPreviewTableOptions.Add(tableRef);
            }
        }

        SelectedDataPreviewTableOption =
            DataPreviewTableOptions.FirstOrDefault(tableRef =>
                string.Equals(tableRef.TableRefId, previousTableRefId, StringComparison.Ordinal))
            ?? DataPreviewTableOptions.FirstOrDefault();
    }

    partial void OnSelectedDataPreviewTableOptionChanged(TableRefListItemViewModel? value)
    {
        CancelDataPreviewWorkbenchLoadForSelectionChange();
        LoadSelectedDataPreviewTableCommand.NotifyCanExecuteChanged();
    }

    partial void OnSelectedDataPreviewTableRefChanged(TableRefListItemViewModel? value)
    {
        DataPreviewWorkbenchErrorMessage = null;
        if (value is not null)
        {
            SelectDataPreviewTableOptionByTableRefId(value.TableRefId);
        }

        LoadSelectedDataPreviewTableCommand.NotifyCanExecuteChanged();
    }
}
