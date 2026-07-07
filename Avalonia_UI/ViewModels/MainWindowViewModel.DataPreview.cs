using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private const int DataPreviewRowLimit = 50;
    private const int DataPreviewRunRefreshAttemptCount = 8;

    private readonly Func<CancellationToken, Task> _dataPreviewRunRefreshDelay;

    private int tableRefsLoadVersion;

    private int dataPreviewLoadVersion;
    private int dataPreviewWorkbenchLoadVersion;

    [ObservableProperty]
    private bool isLoadingTableRefs;

    [ObservableProperty]
    private string tableRefMessage = "Select a run to load table refs.";

    [ObservableProperty]
    private string? tableRefErrorMessage;

    [ObservableProperty]
    private bool isLoadingDataPreview;

    [ObservableProperty]
    private string dataPreviewMessage =
        "Select a run and workflow node to load data preview.";

    [ObservableProperty]
    private string? dataPreviewErrorMessage;

    [ObservableProperty]
    private TableRefListItemViewModel? selectedDataPreviewTableRef;

    [ObservableProperty]
    private DataPreviewStateListItemViewModel? selectedDataPreviewState;

    [ObservableProperty]
    private TableRefListItemViewModel? selectedDataPreviewTableOption;

    [ObservableProperty]
    private TableRefListItemViewModel? loadedDataPreviewTableRef;

    [ObservableProperty]
    private bool isLoadingDataPreviewWorkbench;

    [ObservableProperty]
    private string dataPreviewWorkbenchMessage =
        "Select a run, refresh table refs, then select a table to inspect rows.";

    [ObservableProperty]
    private string? dataPreviewWorkbenchErrorMessage;

    [ObservableProperty]
    private string dataPreviewWorkbenchSearchText = string.Empty;

    [ObservableProperty]
    private string dataPreviewWorkbenchClipboardText = string.Empty;

    [ObservableProperty]
    private string dataPreviewWorkbenchPasteText = string.Empty;

    [ObservableProperty]
    private bool isDataPreviewWorkbenchDraft;

    private string? dataPreviewSourceWorkflowRunId;

    private string? dataPreviewSourceNodeInstanceId;

    private string? dataPreviewSourceLogicalTableId;

    private string? dataPreviewSourceTableRefId;

    private string? dataPreviewSourceRunMode;

    private string? dataPreviewSourceTargetNodeInstanceId;

    private string[] dataPreviewWorkbenchLoadedColumns = [];

    private JsonElement[] dataPreviewWorkbenchLoadedRows = [];

    private string[][] dataPreviewWorkbenchOriginalCellRows = [];

    private string[][] dataPreviewWorkbenchEditableCellRows = [];

    private int dataPreviewWorkbenchOffset;

    private bool dataPreviewWorkbenchHasMore;

    private long dataPreviewWorkbenchRowCount;

    public ObservableCollection<TableRefListItemViewModel> TableRefs { get; } = new();

    public ObservableCollection<DataPreviewStateListItemViewModel> DataPreviewStates { get; } = new();

    public ObservableCollection<TableRefListItemViewModel> DataPreviewTableOptions { get; } = new();

    public ObservableCollection<TableDataPreviewColumnViewModel> DataPreviewColumns { get; } = new();

    public ObservableCollection<TableDataPreviewRowViewModel> DataPreviewRows { get; } =
        new();

    public ObservableCollection<TableDataPreviewColumnViewModel> DataPreviewWorkbenchColumns { get; } = new();

    public ObservableCollection<TableDataPreviewRowViewModel> DataPreviewWorkbenchRows { get; } =
        new();

    private bool CanRefreshSelectedWorkflowNodeDataPreview()
    {
        return CanUseEngineActions
            && SelectedRun is not null
            && SelectedWorkflowDefinitionNode is not null
            && !IsLoadingDataPreview;
    }

    private bool CanShowDataPreviewDetails()
    {
        return CanUseEngineActions
            && !string.IsNullOrWhiteSpace(dataPreviewSourceTableRefId)
            && !IsLoadingDataPreviewWorkbench;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshSelectedWorkflowNodeDataPreview))]
    private async Task RefreshSelectedWorkflowNodeDataPreviewAsync()
    {
        await TryRefreshSelectedWorkflowNodeDataPreviewAsync();
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
                    tableRef => string.Equals(tableRef.TableRefId, tableRefId, StringComparison.Ordinal));
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

    private async Task<bool> TryRefreshSelectedWorkflowNodeDataPreviewAsync(
        bool notifyResult = true)
    {
        if (SelectedRun is null || SelectedWorkflowDefinitionNode is null)
        {
            return false;
        }

        var requestedRunId = SelectedRun.WorkflowRunId;
        var requestedNodeInstanceId = SelectedWorkflowDefinitionNode.NodeInstanceId;
        var requestVersion = ++dataPreviewLoadVersion;
        IsLoadingDataPreview = true;
        DataPreviewMessage = F("format.loading_data_preview", requestedNodeInstanceId);
        DataPreviewErrorMessage = null;

        try
        {
            var nodeRunsResponse = await _apiClient.ListNodeRunsAsync(
                BuildSettings(),
                requestedRunId,
                _shutdown.Token);

            if (IsStaleDataPreviewRequest(requestVersion, requestedRunId, requestedNodeInstanceId))
            {
                return false;
            }

            if (!nodeRunsResponse.Ok || nodeRunsResponse.Data is null)
            {
                DataPreviewMessage = T("data_preview.refresh_failed");
                DataPreviewErrorMessage = DescribeError(nodeRunsResponse);
                if (notifyResult)
                {
                    ShowDataPreviewNotification(UiNotificationKind.Error);
                }

                return false;
            }

            var nodeRun = nodeRunsResponse.Data.FirstOrDefault(item =>
                string.Equals(
                    item.NodeInstanceId,
                    requestedNodeInstanceId,
                    StringComparison.Ordinal));
            if (nodeRun is null)
            {
                DataPreviewMessage =
                    F("format.data_preview_node_run_not_found", requestedNodeInstanceId);
                if (notifyResult)
                {
                    ShowDataPreviewNotification(UiNotificationKind.Warning);
                }

                return false;
            }

            var tableRefsResponse = await _apiClient.ListTableRefsAsync(
                BuildSettings(),
                requestedRunId,
                _shutdown.Token);

            if (IsStaleDataPreviewRequest(requestVersion, requestedRunId, requestedNodeInstanceId))
            {
                return false;
            }

            if (!tableRefsResponse.Ok || tableRefsResponse.Data is null)
            {
                DataPreviewMessage = T("data_preview.refresh_failed");
                DataPreviewErrorMessage = DescribeError(tableRefsResponse);
                if (notifyResult)
                {
                    ShowDataPreviewNotification(UiNotificationKind.Error);
                }

                return false;
            }

            var tableRef = tableRefsResponse.Data
                .Where(item =>
                    string.Equals(item.NodeRunId, nodeRun.NodeRunId, StringComparison.Ordinal)
                    && IsReadablePublishedTableRef(item))
                .OrderByDescending(item => item.Version)
                .ThenByDescending(item => item.CreatedAt)
                .FirstOrDefault();
            if (tableRef is null)
            {
                DataPreviewMessage =
                    F("format.data_preview_table_ref_not_found", requestedNodeInstanceId);
                if (notifyResult)
                {
                    ShowDataPreviewNotification(UiNotificationKind.Warning);
                }

                return false;
            }

            var rowsResponse = await _apiClient.GetTableDataRowsAsync(
                BuildSettings(),
                tableRef.TableRefId,
                offset: 0,
                limit: DataPreviewRowLimit,
                cancellationToken: _shutdown.Token);

            if (IsStaleDataPreviewRequest(requestVersion, requestedRunId, requestedNodeInstanceId))
            {
                return false;
            }

            if (!rowsResponse.Ok || rowsResponse.Data is null)
            {
                DataPreviewMessage = T("data_preview.refresh_failed");
                DataPreviewErrorMessage = DescribeError(rowsResponse);
                if (notifyResult)
                {
                    ShowDataPreviewNotification(UiNotificationKind.Error);
                }

                return false;
            }

            LoadDataPreviewRows(rowsResponse.Data);
            UpdateDataPreviewSource(
                requestedRunId,
                requestedNodeInstanceId,
                tableRef.LogicalTableId,
                tableRef.TableRefId,
                SelectedRun?.RunMode,
                SelectedRun?.TargetNodeInstanceId);
            DataPreviewMessage = F(
                "format.loaded_data_preview",
                rowsResponse.Data.Rows.Length,
                rowsResponse.Data.RowCount,
                tableRef.LogicalTableId);
            if (notifyResult)
            {
                ShowDataPreviewNotification(UiNotificationKind.Success);
            }

            return true;
        }
        finally
        {
            if (requestVersion == dataPreviewLoadVersion)
            {
                IsLoadingDataPreview = false;
            }
        }
    }

    private async Task RefreshSelectedWorkflowNodeDataPreviewAfterRunStartAsync(
        string workflowRunId)
    {
        for (var attempt = 0; attempt < DataPreviewRunRefreshAttemptCount; attempt++)
        {
            await LoadRunsAsync(workflowRunId);
            var loadedCurrentPreview = false;
            if (CanRefreshSelectedWorkflowNodeDataPreview())
            {
                loadedCurrentPreview = await TryRefreshSelectedWorkflowNodeDataPreviewAsync(
                    notifyResult: false);
            }

            if (loadedCurrentPreview)
            {
                ShowDataPreviewNotification(UiNotificationKind.Success);
                return;
            }

            if (SelectedRun is not null && IsTerminalRunStatus(SelectedRun.Status))
            {
                ShowDataPreviewNotification(
                    HasDataPreviewError ? UiNotificationKind.Error : UiNotificationKind.Warning);
                return;
            }

            if (attempt + 1 < DataPreviewRunRefreshAttemptCount)
            {
                await _dataPreviewRunRefreshDelay(_shutdown.Token);
            }
        }

        ShowDataPreviewNotification(
            HasDataPreviewError ? UiNotificationKind.Error : UiNotificationKind.Warning);
    }

    private async Task SelectLatestReadableOutputNodeForRunAsync(string workflowRunId)
    {
        var nodeRunsResponse = await _apiClient.ListNodeRunsAsync(
            BuildSettings(),
            workflowRunId,
            _shutdown.Token);
        if (!nodeRunsResponse.Ok || nodeRunsResponse.Data is null)
        {
            return;
        }

        var tableRefsResponse = await _apiClient.ListTableRefsAsync(
            BuildSettings(),
            workflowRunId,
            _shutdown.Token);
        if (!tableRefsResponse.Ok || tableRefsResponse.Data is null)
        {
            return;
        }

        var nodeInstanceIdsWithReadableOutput = tableRefsResponse.Data
            .Where(IsReadablePublishedTableRef)
            .Join(
                nodeRunsResponse.Data,
                tableRef => tableRef.NodeRunId,
                nodeRun => nodeRun.NodeRunId,
                (_, nodeRun) => nodeRun.NodeInstanceId)
            .ToHashSet(StringComparer.Ordinal);
        var latestOutputNode = WorkflowDefinitionDraftNodes
            .Reverse()
            .FirstOrDefault(node => nodeInstanceIdsWithReadableOutput.Contains(node.NodeInstanceId));
        if (latestOutputNode is not null)
        {
            SelectedWorkflowDefinitionNode = latestOutputNode;
        }
    }

    private bool IsStaleDataPreviewRequest(
        int requestVersion,
        string requestedRunId,
        string requestedNodeInstanceId)
    {
        return requestVersion != dataPreviewLoadVersion
            || !string.Equals(
                SelectedRun?.WorkflowRunId,
                requestedRunId,
                StringComparison.Ordinal)
            || !string.Equals(
                SelectedWorkflowDefinitionNode?.NodeInstanceId,
                requestedNodeInstanceId,
                StringComparison.Ordinal);
    }

    private static bool IsReadablePublishedTableRef(TableRefDto tableRef)
    {
        return string.Equals(
                tableRef.LifecycleStatus,
                "PUBLISHED",
                StringComparison.OrdinalIgnoreCase)
            && tableRef.Capabilities.Any(capability =>
                string.Equals(capability, "READ", StringComparison.OrdinalIgnoreCase));
    }

    private void ResetDataPreviewSelectionState()
    {
        dataPreviewLoadVersion++;
        IsLoadingDataPreview = false;
        DataPreviewMessage = T("status.select_run_and_workflow_node_data_preview");
        DataPreviewErrorMessage = null;
        ClearDataPreviewSourceIfNoPreviewRows();
        RefreshSelectedWorkflowNodeDataPreviewCommand.NotifyCanExecuteChanged();
        ShowDataPreviewDetailsCommand.NotifyCanExecuteChanged();
    }

    private void ClearDataPreviewSourceIfNoPreviewRows()
    {
        if (HasDataPreviewColumns || HasDataPreviewRows)
        {
            return;
        }

        dataPreviewSourceWorkflowRunId = null;
        dataPreviewSourceNodeInstanceId = null;
        dataPreviewSourceLogicalTableId = null;
        dataPreviewSourceTableRefId = null;
        dataPreviewSourceRunMode = null;
        dataPreviewSourceTargetNodeInstanceId = null;
        OnPropertyChanged(nameof(DataPreviewSourceText));
    }

    private void LoadDataPreviewRows(TableDataRowsDto rows)
    {
        var grid = DataPreviewTableGridBuilder.BuildGrid(rows);

        DataPreviewColumns.Clear();
        foreach (var column in grid.Columns)
        {
            DataPreviewColumns.Add(new TableDataPreviewColumnViewModel(column));
        }

        DataPreviewRows.Clear();
        foreach (var row in grid.CellRows)
        {
            DataPreviewRows.Add(
                new TableDataPreviewRowViewModel(
                    row
                        .Select(value => new TableDataPreviewCellViewModel(value))
                        .ToArray()));
        }

        NotifyDataPreviewRowsChanged();
    }

    private void UpdateDataPreviewSource(
        string workflowRunId,
        string nodeInstanceId,
        string logicalTableId,
        string tableRefId,
        string? runMode,
        string? targetNodeInstanceId)
    {
        dataPreviewSourceWorkflowRunId = workflowRunId;
        dataPreviewSourceNodeInstanceId = nodeInstanceId;
        dataPreviewSourceLogicalTableId = logicalTableId;
        dataPreviewSourceTableRefId = tableRefId;
        dataPreviewSourceRunMode = runMode;
        dataPreviewSourceTargetNodeInstanceId = targetNodeInstanceId;
        OnPropertyChanged(nameof(DataPreviewSourceText));
        ShowDataPreviewDetailsCommand.NotifyCanExecuteChanged();
    }

    private void NotifyDataPreviewRowsChanged()
    {
        OnPropertyChanged(nameof(HasDataPreviewColumns));
        OnPropertyChanged(nameof(HasDataPreviewRows));
    }

    partial void OnIsLoadingTableRefsChanged(bool value)
    {
        OnPropertyChanged(nameof(IsDataBusy));
        RefreshTableRefsCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsLoadingDataPreviewChanged(bool value)
    {
        OnPropertyChanged(nameof(IsDataPreviewBusy));
        RefreshSelectedWorkflowNodeDataPreviewCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
    }

    partial void OnTableRefErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasTableRefError));
    }

    partial void OnDataPreviewErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasDataPreviewError));
    }

    partial void OnDataPreviewWorkbenchErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasDataPreviewWorkbenchError));
    }

}
