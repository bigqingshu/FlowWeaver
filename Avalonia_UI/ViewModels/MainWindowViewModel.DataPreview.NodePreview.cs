using System;
using System.Linq;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanRefreshSelectedWorkflowNodeDataPreview()
    {
        return CanUseEngineActions
            && SelectedRun is not null
            && SelectedWorkflowDefinitionNode is not null
            && !IsLoadingDataPreview;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshSelectedWorkflowNodeDataPreview))]
    private async Task RefreshSelectedWorkflowNodeDataPreviewAsync()
    {
        await TryRefreshSelectedWorkflowNodeDataPreviewAsync();
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

    partial void OnIsLoadingDataPreviewChanged(bool value)
    {
        OnPropertyChanged(nameof(IsDataPreviewBusy));
        RefreshSelectedWorkflowNodeDataPreviewCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
    }

    partial void OnDataPreviewErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasDataPreviewError));
    }
}
