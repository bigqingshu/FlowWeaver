using System;
using System.Linq;
using System.Threading.Tasks;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanShowDataPreviewDetails()
    {
        return CanUseEngineActions
            && !string.IsNullOrWhiteSpace(dataPreviewSourceTableRefId)
            && !IsLoadingDataPreviewWorkbench;
    }

    [RelayCommand(CanExecute = nameof(CanShowDataPreviewDetails))]
    private async Task ShowDataPreviewDetailsAsync()
    {
        var tableRefId = dataPreviewSourceTableRefId;
        var workflowRunId = dataPreviewSourceWorkflowRunId;
        if (string.IsNullOrWhiteSpace(tableRefId) || string.IsNullOrWhiteSpace(workflowRunId))
        {
            return;
        }

        var target = TableRefs.FirstOrDefault(
            tableRef => string.Equals(tableRef.TableRefId, tableRefId, StringComparison.Ordinal));
        if (target is null)
        {
            var response = await _apiClient.ListTableRefsAsync(
                BuildSettings(),
                workflowRunId,
                _shutdown.Token);
            if (response.Ok && response.Data is not null)
            {
                TableRefs.Clear();
                foreach (var tableRef in response.Data)
                {
                    TableRefs.Add(new TableRefListItemViewModel(tableRef));
                }

                RebuildDataPreviewStates(preferredTableRefId: tableRefId);
                TableRefMessage = F("format.loaded_table_refs", TableRefs.Count);
                TableRefErrorMessage = null;
                target = TableRefs.FirstOrDefault(
                    tableRef => string.Equals(
                        tableRef.TableRefId,
                        tableRefId,
                        StringComparison.Ordinal));
            }
            else
            {
                DataPreviewWorkbenchMessage = T("data_preview.workbench_load_failed");
                DataPreviewWorkbenchErrorMessage = DescribeError(response);
                return;
            }
        }

        if (target is null)
        {
            DataPreviewWorkbenchMessage = T("data_preview.workbench_table_not_found");
            DataPreviewWorkbenchErrorMessage = null;
            return;
        }

        SelectDataPreviewTableOptionByTableRefId(target.TableRefId);
        SelectedDataPreviewTableRef = target;
        SelectedShellPageKey = ShellPageKey.DataPreview;
        await LoadSelectedDataPreviewTableAsync();
    }
}
