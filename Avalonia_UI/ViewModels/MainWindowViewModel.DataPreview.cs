using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text;
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

    public bool HasTableRefError => !string.IsNullOrWhiteSpace(TableRefErrorMessage);

    public bool HasDataPreviewError =>
        !string.IsNullOrWhiteSpace(DataPreviewErrorMessage);

    public bool HasDataPreviewWorkbenchError =>
        !string.IsNullOrWhiteSpace(DataPreviewWorkbenchErrorMessage);

    public bool HasDataPreviewColumns => DataPreviewColumns.Count > 0;

    public bool HasDataPreviewRows => DataPreviewRows.Count > 0;

    public bool HasDataPreviewWorkbenchColumns => DataPreviewWorkbenchColumns.Count > 0;

    public bool HasDataPreviewWorkbenchRows => DataPreviewWorkbenchRows.Count > 0;

    public bool HasDataPreviewWorkbenchClipboardText =>
        !string.IsNullOrEmpty(DataPreviewWorkbenchClipboardText);

    public bool HasDataPreviewWorkbenchPasteText =>
        !string.IsNullOrWhiteSpace(DataPreviewWorkbenchPasteText);

    public bool IsDataPreviewWorkbenchDirty =>
        dataPreviewWorkbenchEditableCellRows.Length > 0
        && !DataPreviewWorkbenchCellRowsEqual(
            dataPreviewWorkbenchOriginalCellRows,
            dataPreviewWorkbenchEditableCellRows);

    public string DataPreviewWorkbenchDirtyStateText => IsDataPreviewWorkbenchDirty
        ? T("data_preview.dirty")
        : T("data_preview.clean");

    public bool CanSaveDataPreviewWorkbenchAsDraft =>
        LoadedDataPreviewTableRef?.HasCapability("SAVE_AS") == true;

    public string DataPreviewWorkbenchSavePolicyText =>
        LoadedDataPreviewTableRef is not { } tableRef
            ? T("data_preview.save_policy_local_draft")
            : CanSaveDataPreviewWorkbenchAsDraft
                ? F(
                    "format.data_preview_save_policy_save_as",
                    tableRef.StorageKind,
                    tableRef.CapabilitiesText)
                : F(
                    "format.data_preview_save_policy_read_only",
                    tableRef.StorageKind,
                    tableRef.CapabilitiesText);

    public string DataPreviewWorkbenchPageText => F(
        "format.data_preview_workbench_page",
        dataPreviewWorkbenchLoadedRows.Length == 0 ? 0 : dataPreviewWorkbenchOffset + 1,
        dataPreviewWorkbenchOffset + dataPreviewWorkbenchLoadedRows.Length,
        dataPreviewWorkbenchRowCount);

    public string DataPreviewSourceText =>
        !string.IsNullOrWhiteSpace(dataPreviewSourceWorkflowRunId)
        && !string.IsNullOrWhiteSpace(dataPreviewSourceNodeInstanceId)
        && !string.IsNullOrWhiteSpace(dataPreviewSourceLogicalTableId)
            ? FormatDataPreviewSourceText()
            : T("data_preview.source_not_loaded");

    public bool IsDataPreviewBusy => IsLoadingDataPreview;

    public bool IsDataPreviewWorkbenchBusy => IsLoadingDataPreviewWorkbench;

    public string DataPreviewWorkbenchPendingText => T("data_preview.workbench_pending");

    public string DataPreviewWorkbenchSourceText =>
        IsDataPreviewWorkbenchDraft
            ? T("data_preview.workbench_draft_source")
            : LoadedDataPreviewTableRef is not { } tableRef
            ? T("data_preview.workbench_source_not_loaded")
            : F(
                "format.data_preview_workbench_source",
                tableRef.WorkflowRunId,
                tableRef.NodeRunId,
                tableRef.LogicalTableId,
                tableRef.StorageKind);

    public string DataPreviewTableSelectorText => T("data_preview.table_selector");

    public string DataPreviewStateSelectorText => T("data_preview.state_selector");

    public string DataPreviewLoadSelectedTableText => T("data_preview.load_selected_table");

    public string DataPreviewWorkbenchRefreshText => T("data_preview.workbench_refresh");

    public string DataPreviewDetailsText => T("data_preview.details");

    public string DataPreviewSearchText => T("data_preview.search");

    public string DataPreviewSearchWatermarkText => T("data_preview.search_watermark");

    public string DataPreviewCopyTsvText => T("data_preview.copy_tsv");

    public string DataPreviewPasteText => T("data_preview.paste_text");

    public string DataPreviewPasteWatermarkText => T("data_preview.paste_watermark");

    public string DataPreviewParsePasteText => T("data_preview.parse_paste");

    public string DataPreviewRestoreDraftText => T("data_preview.restore_draft");

    public string DataPreviewSaveAsText => T("data_preview.save_as");

    public string DataPreviewPreviousPageText => T("data_preview.previous_page");
    public string DataPreviewNextPageText => T("data_preview.next_page");

    public string DataPreviewSectionText => T("definition.data_preview");

    public string DataPreviewEmptyText => T("definition.data_preview_empty");

    public string DataPreviewPendingText => T("definition.data_preview_pending");

    public string DataPreviewRefreshText => T("definition.data_preview_refresh");

    public string PreviewSelectedNodeText => T("definition.preview_selected_node");

    public string TableRefsSectionText => T("data.table_refs");

    private bool CanRefreshTableRefs()
    {
        return CanUseEngineActions && SelectedRun is not null && !IsLoadingTableRefs;
    }

    private bool CanRefreshSelectedWorkflowNodeDataPreview()
    {
        return CanUseEngineActions
            && SelectedRun is not null
            && SelectedWorkflowDefinitionNode is not null
            && !IsLoadingDataPreview;
    }

    private bool CanLoadSelectedDataPreviewTable()
    {
        return CanUseEngineActions
            && SelectedDataPreviewTableOption is not null
            && !IsLoadingDataPreviewWorkbench;
    }

    private bool CanLoadPreviousDataPreviewWorkbenchPage()
    {
        return CanUseEngineActions
            && LoadedDataPreviewTableRef is not null
            && !IsLoadingDataPreviewWorkbench
            && dataPreviewWorkbenchOffset > 0;
    }

    private bool CanLoadNextDataPreviewWorkbenchPage()
    {
        return CanUseEngineActions
            && LoadedDataPreviewTableRef is not null
            && !IsLoadingDataPreviewWorkbench
            && dataPreviewWorkbenchHasMore;
    }

    private bool CanCopyDataPreviewWorkbenchTsv()
    {
        return HasDataPreviewWorkbenchColumns
            && HasDataPreviewWorkbenchRows;
    }

    private bool CanParseDataPreviewWorkbenchPaste()
    {
        return HasDataPreviewWorkbenchPasteText
            && !IsLoadingDataPreviewWorkbench;
    }

    private bool CanRestoreDataPreviewWorkbenchDraft()
    {
        return IsDataPreviewWorkbenchDirty
            && !IsLoadingDataPreviewWorkbench;
    }

    private bool CanSaveDataPreviewWorkbenchAs()
    {
        return IsDataPreviewWorkbenchDirty
            && CanSaveDataPreviewWorkbenchAsDraft
            && !IsLoadingDataPreviewWorkbench;
    }

    private bool CanShowDataPreviewDetails()
    {
        return CanUseEngineActions
            && !string.IsNullOrWhiteSpace(dataPreviewSourceTableRefId)
            && !IsLoadingDataPreviewWorkbench;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshTableRefs))]
    private async Task RefreshTableRefsAsync()
    {
        if (SelectedRun is null)
        {
            return;
        }

        var requestedRunId = SelectedRun.WorkflowRunId;
        var requestVersion = ++tableRefsLoadVersion;
        IsLoadingTableRefs = true;
        TableRefMessage = F("format.loading_table_refs_for", requestedRunId);
        TableRefErrorMessage = null;

        try
        {
            var response = await _apiClient.ListTableRefsAsync(
                BuildSettings(),
                requestedRunId,
                _shutdown.Token);

            if (
                SelectedRun?.WorkflowRunId != requestedRunId
                || requestVersion != tableRefsLoadVersion)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                var previousSelectedTableRefId = SelectedDataPreviewTableRef?.TableRefId;
                var previousSelectedStateKey = SelectedDataPreviewState?.StateKey;
                var previousSelectedTableOptionId =
                    SelectedDataPreviewTableOption?.TableRefId ?? previousSelectedTableRefId;
                TableRefs.Clear();
                foreach (var tableRef in response.Data)
                {
                    TableRefs.Add(new TableRefListItemViewModel(tableRef));
                }

                RebuildDataPreviewStates(
                    previousSelectedStateKey,
                    previousSelectedTableOptionId);
                SelectedDataPreviewTableRef = TableRefs.FirstOrDefault(
                    tableRef => tableRef.TableRefId == previousSelectedTableRefId)
                    ?? SelectedDataPreviewTableOption
                    ?? TableRefs.FirstOrDefault();

                TableRefMessage = F("format.loaded_table_refs", TableRefs.Count);
                return;
            }

            TableRefMessage = T("data.table_ref_refresh_failed");
            TableRefErrorMessage = DescribeError(response);
        }
        finally
        {
            if (requestVersion == tableRefsLoadVersion)
            {
                IsLoadingTableRefs = false;
            }
        }
    }

    [RelayCommand(CanExecute = nameof(CanRefreshSelectedWorkflowNodeDataPreview))]
    private async Task RefreshSelectedWorkflowNodeDataPreviewAsync()
    {
        await TryRefreshSelectedWorkflowNodeDataPreviewAsync();
    }

    [RelayCommand(CanExecute = nameof(CanLoadSelectedDataPreviewTable))]
    private async Task LoadSelectedDataPreviewTableAsync()
    {
        await LoadDataPreviewWorkbenchTablePageAsync(SelectedDataPreviewTableOption, 0);
    }

    [RelayCommand(CanExecute = nameof(CanLoadPreviousDataPreviewWorkbenchPage))]
    private async Task LoadPreviousDataPreviewWorkbenchPageAsync()
    {
        await LoadDataPreviewWorkbenchTablePageAsync(
            LoadedDataPreviewTableRef,
            Math.Max(0, dataPreviewWorkbenchOffset - DataPreviewRowLimit));
    }

    [RelayCommand(CanExecute = nameof(CanLoadNextDataPreviewWorkbenchPage))]
    private async Task LoadNextDataPreviewWorkbenchPageAsync()
    {
        await LoadDataPreviewWorkbenchTablePageAsync(
            LoadedDataPreviewTableRef,
            dataPreviewWorkbenchOffset + DataPreviewRowLimit);
    }

    [RelayCommand(CanExecute = nameof(CanCopyDataPreviewWorkbenchTsv))]
    private void CopyDataPreviewWorkbenchTsv()
    {
        DataPreviewWorkbenchClipboardText = BuildDataPreviewWorkbenchTsv();
    }

    [RelayCommand(CanExecute = nameof(CanParseDataPreviewWorkbenchPaste))]
    private void ParseDataPreviewWorkbenchPaste()
    {
        DataPreviewWorkbenchErrorMessage = null;
        if (!TryParseDelimitedTable(
                DataPreviewWorkbenchPasteText,
                out var columns,
                out var rows,
                out var errorKey))
        {
            DataPreviewWorkbenchMessage = T("data_preview.workbench_parse_failed");
            DataPreviewWorkbenchErrorMessage = errorKey is null ? null : T(errorKey);
            return;
        }

        LoadedDataPreviewTableRef = null;
        LoadDataPreviewWorkbenchRows(
            new TableDataRowsDto
            {
                TableRefId = "local-draft",
                Offset = 0,
                Limit = rows.Length,
                RowCount = rows.Length,
                Columns = columns,
                Rows = rows,
                HasMore = false,
            },
            isDraft: true);
        DataPreviewWorkbenchMessage = F(
            "format.data_preview_imported_rows",
            rows.Length,
            columns.Length);
    }

    [RelayCommand(CanExecute = nameof(CanRestoreDataPreviewWorkbenchDraft))]
    private void RestoreDataPreviewWorkbenchDraft()
    {
        dataPreviewWorkbenchEditableCellRows = CloneCellRows(dataPreviewWorkbenchOriginalCellRows);
        ApplyDataPreviewWorkbenchSearch();
        NotifyDataPreviewWorkbenchDirtyStateChanged();
        DataPreviewWorkbenchClipboardText = string.Empty;
        DataPreviewWorkbenchMessage = T("data_preview.draft_restored");
    }

    [RelayCommand(CanExecute = nameof(CanSaveDataPreviewWorkbenchAs))]
    private void SaveDataPreviewWorkbenchAs()
    {
        DataPreviewWorkbenchMessage = T("data_preview.save_as_api_pending");
        DataPreviewWorkbenchErrorMessage = null;
    }

    private async Task LoadDataPreviewWorkbenchTablePageAsync(
        TableRefListItemViewModel? requestedTableRef,
        int offset)
    {
        if (requestedTableRef is null)
        {
            return;
        }

        var requestedTableRefId = requestedTableRef.TableRefId;
        var requestVersion = ++dataPreviewWorkbenchLoadVersion;
        IsLoadingDataPreviewWorkbench = true;
        DataPreviewWorkbenchMessage = F(
            "format.loading_data_preview_table",
            requestedTableRef.LogicalTableId);
        DataPreviewWorkbenchErrorMessage = null;

        try
        {
            var response = await _apiClient.GetTableDataRowsAsync(
                BuildSettings(),
                requestedTableRefId,
                offset: Math.Max(0, offset),
                limit: DataPreviewRowLimit,
                cancellationToken: _shutdown.Token);

            if (IsStaleDataPreviewWorkbenchRequest(requestVersion))
            {
                return;
            }

            if (!response.Ok || response.Data is null)
            {
                DataPreviewWorkbenchMessage = T("data_preview.workbench_load_failed");
                DataPreviewWorkbenchErrorMessage = DescribeError(response);
                return;
            }

            LoadDataPreviewWorkbenchRows(response.Data);
            LoadedDataPreviewTableRef = requestedTableRef;
            UpdateDataPreviewWorkbenchLoadedMessage();
        }
        finally
        {
            if (requestVersion == dataPreviewWorkbenchLoadVersion)
            {
                IsLoadingDataPreviewWorkbench = false;
            }
        }
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

    private bool IsStaleDataPreviewWorkbenchRequest(int requestVersion)
    {
        return requestVersion != dataPreviewWorkbenchLoadVersion;
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

    private void RebuildDataPreviewStates(
        string? preferredStateKey = null,
        string? preferredTableRefId = null)
    {
        DataPreviewStates.Clear();
        foreach (var state in DataPreviewStateListItemViewModel.FromTableRefs(TableRefs))
        {
            DataPreviewStates.Add(state);
        }

        var selectedState =
            FindDataPreviewStateByKey(preferredStateKey)
            ?? FindDataPreviewStateByTableRefId(preferredTableRefId)
            ?? DataPreviewStates.FirstOrDefault();
        SelectedDataPreviewState = selectedState;

        if (!string.IsNullOrWhiteSpace(preferredTableRefId))
        {
            SelectedDataPreviewTableOption =
                DataPreviewTableOptions.FirstOrDefault(tableRef =>
                    string.Equals(tableRef.TableRefId, preferredTableRefId, StringComparison.Ordinal))
                ?? SelectedDataPreviewTableOption;
        }
    }

    private DataPreviewStateListItemViewModel? FindDataPreviewStateByKey(string? stateKey)
    {
        return string.IsNullOrWhiteSpace(stateKey)
            ? null
            : DataPreviewStates.FirstOrDefault(state =>
                string.Equals(state.StateKey, stateKey, StringComparison.Ordinal));
    }

    private DataPreviewStateListItemViewModel? FindDataPreviewStateByTableRefId(string? tableRefId)
    {
        return string.IsNullOrWhiteSpace(tableRefId)
            ? null
            : DataPreviewStates.FirstOrDefault(state =>
                state.TableRefs.Any(tableRef =>
                    string.Equals(tableRef.TableRefId, tableRefId, StringComparison.Ordinal)));
    }

    private void SelectDataPreviewTableOptionByTableRefId(string? tableRefId)
    {
        var state = FindDataPreviewStateByTableRefId(tableRefId);
        if (state is null)
        {
            return;
        }

        SelectedDataPreviewState = state;
        SelectedDataPreviewTableOption =
            DataPreviewTableOptions.FirstOrDefault(tableRef =>
                string.Equals(tableRef.TableRefId, tableRefId, StringComparison.Ordinal))
            ?? SelectedDataPreviewTableOption;
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

    private void ResetDataPreviewWorkbenchState()
    {
        dataPreviewWorkbenchLoadVersion++;
        IsLoadingDataPreviewWorkbench = false;
        SelectedDataPreviewState = null;
        DataPreviewStates.Clear();
        SelectedDataPreviewTableOption = null;
        DataPreviewTableOptions.Clear();
        SelectedDataPreviewTableRef = null;
        ResetDataPreviewWorkbenchLoadedState();
        DataPreviewWorkbenchColumns.Clear();
        DataPreviewWorkbenchRows.Clear();
        DataPreviewWorkbenchMessage = T("data_preview.workbench_select_table");
        DataPreviewWorkbenchErrorMessage = null;
        NotifyDataPreviewWorkbenchRowsChanged();
        LoadSelectedDataPreviewTableCommand.NotifyCanExecuteChanged();
    }

    private void LoadDataPreviewRows(TableDataRowsDto rows)
    {
        DataPreviewColumns.Clear();
        foreach (var column in rows.Columns)
        {
            DataPreviewColumns.Add(new TableDataPreviewColumnViewModel(column));
        }

        DataPreviewRows.Clear();
        foreach (var row in rows.Rows)
        {
            DataPreviewRows.Add(
                new TableDataPreviewRowViewModel(
                    rows.Columns
                        .Select(
                            column =>
                                new TableDataPreviewCellViewModel(
                                    FormatDataPreviewCell(row, column)))
                        .ToArray()));
        }

        NotifyDataPreviewRowsChanged();
    }

    private void LoadDataPreviewWorkbenchRows(TableDataRowsDto rows, bool isDraft = false)
    {
        IsDataPreviewWorkbenchDraft = isDraft;
        dataPreviewWorkbenchLoadedColumns = rows.Columns.ToArray();
        dataPreviewWorkbenchLoadedRows = rows.Rows.Select(row => row.Clone()).ToArray();
        dataPreviewWorkbenchOriginalCellRows = dataPreviewWorkbenchLoadedRows
            .Select(row => CreateCellRow(row, dataPreviewWorkbenchLoadedColumns))
            .ToArray();
        dataPreviewWorkbenchEditableCellRows = CloneCellRows(dataPreviewWorkbenchOriginalCellRows);
        dataPreviewWorkbenchOffset = rows.Offset;
        dataPreviewWorkbenchHasMore = rows.HasMore;
        dataPreviewWorkbenchRowCount = rows.RowCount;
        DataPreviewWorkbenchClipboardText = string.Empty;
        ApplyDataPreviewWorkbenchSearch();
        NotifyDataPreviewWorkbenchPagingChanged();
        NotifyDataPreviewWorkbenchDirtyStateChanged();
        OnPropertyChanged(nameof(DataPreviewWorkbenchSourceText));
    }

    private void ResetDataPreviewWorkbenchLoadedState()
    {
        LoadedDataPreviewTableRef = null;
        dataPreviewWorkbenchLoadedColumns = [];
        dataPreviewWorkbenchLoadedRows = [];
        dataPreviewWorkbenchOriginalCellRows = [];
        dataPreviewWorkbenchEditableCellRows = [];
        dataPreviewWorkbenchOffset = 0;
        dataPreviewWorkbenchHasMore = false;
        dataPreviewWorkbenchRowCount = 0;
        DataPreviewWorkbenchClipboardText = string.Empty;
        IsDataPreviewWorkbenchDraft = false;
        NotifyDataPreviewWorkbenchPagingChanged();
        NotifyDataPreviewWorkbenchDirtyStateChanged();
    }

    private void ApplyDataPreviewWorkbenchSearch()
    {
        var filter = NormalizeFilter(DataPreviewWorkbenchSearchText);
        var visibleRowIndexes = Enumerable.Range(0, dataPreviewWorkbenchEditableCellRows.Length);
        if (filter is not null)
        {
            visibleRowIndexes = visibleRowIndexes
                .Where(rowIndex => DataPreviewWorkbenchRowMatches(rowIndex, filter))
                .ToArray();
        }

        DataPreviewWorkbenchColumns.Clear();
        foreach (var column in dataPreviewWorkbenchLoadedColumns)
        {
            DataPreviewWorkbenchColumns.Add(new TableDataPreviewColumnViewModel(column));
        }

        DataPreviewWorkbenchRows.Clear();
        foreach (var rowIndex in visibleRowIndexes)
        {
            DataPreviewWorkbenchRows.Add(CreateDataPreviewWorkbenchRow(rowIndex));
        }

        NotifyDataPreviewWorkbenchRowsChanged();
    }

    private TableDataPreviewRowViewModel CreateDataPreviewWorkbenchRow(int rowIndex)
    {
        return new TableDataPreviewRowViewModel(
            dataPreviewWorkbenchEditableCellRows[rowIndex]
                .Select(
                    (value, columnIndex) =>
                        new TableDataPreviewCellViewModel(
                            value,
                            updatedValue => UpdateDataPreviewWorkbenchCell(
                                rowIndex,
                                columnIndex,
                                updatedValue)))
                .ToArray());
    }

    private bool DataPreviewWorkbenchRowMatches(int rowIndex, string filter)
    {
        return dataPreviewWorkbenchEditableCellRows[rowIndex].Any(
            value => value.Contains(
                filter,
                StringComparison.OrdinalIgnoreCase));
    }

    private static string[] CreateCellRow(JsonElement row, string[] columns)
    {
        return columns.Select(column => FormatDataPreviewCell(row, column)).ToArray();
    }

    private static string[][] CloneCellRows(string[][] rows)
    {
        return rows.Select(row => row.ToArray()).ToArray();
    }

    private void UpdateDataPreviewWorkbenchCell(
        int rowIndex,
        int columnIndex,
        string value)
    {
        if (rowIndex < 0
            || rowIndex >= dataPreviewWorkbenchEditableCellRows.Length
            || columnIndex < 0
            || columnIndex >= dataPreviewWorkbenchEditableCellRows[rowIndex].Length)
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

    private static bool DataPreviewWorkbenchCellRowsEqual(string[][] left, string[][] right)
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

    private string BuildDataPreviewWorkbenchTsv()
    {
        var builder = new StringBuilder();
        builder.AppendLine(string.Join("\t", DataPreviewWorkbenchColumns.Select(column => EscapeTsv(column.Name))));
        foreach (var row in DataPreviewWorkbenchRows)
        {
            builder.AppendLine(string.Join("\t", row.Cells.Select(cell => EscapeTsv(cell.Text))));
        }

        return builder.ToString().TrimEnd('\r', '\n');
    }

    private static string EscapeTsv(string value)
    {
        return value
            .Replace("\r\n", " ", StringComparison.Ordinal)
            .Replace("\r", " ", StringComparison.Ordinal)
            .Replace("\n", " ", StringComparison.Ordinal)
            .Replace('\t', ' ');
    }

    private static bool TryParseDelimitedTable(
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

    private void UpdateDataPreviewWorkbenchLoadedMessage()
    {
        if (LoadedDataPreviewTableRef is null)
        {
            return;
        }

        var filter = NormalizeFilter(DataPreviewWorkbenchSearchText);
        DataPreviewWorkbenchMessage = filter is null
            ? F(
                "format.loaded_data_preview_table_rows",
                dataPreviewWorkbenchLoadedRows.Length,
                dataPreviewWorkbenchRowCount,
                LoadedDataPreviewTableRef.LogicalTableId)
            : F(
                "format.data_preview_search_matches",
                DataPreviewWorkbenchRows.Count,
                dataPreviewWorkbenchLoadedRows.Length,
                filter);
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

    private string FormatDataPreviewSourceText()
    {
        if (string.Equals(
                dataPreviewSourceRunMode,
                "preview_to_node",
                StringComparison.OrdinalIgnoreCase))
        {
            return F(
                "format.data_preview_source_preview",
                dataPreviewSourceWorkflowRunId!,
                string.IsNullOrWhiteSpace(dataPreviewSourceTargetNodeInstanceId)
                    ? dataPreviewSourceNodeInstanceId!
                    : dataPreviewSourceTargetNodeInstanceId!,
                dataPreviewSourceLogicalTableId!);
        }

        return F(
            "format.data_preview_source_full",
            dataPreviewSourceWorkflowRunId!,
            dataPreviewSourceNodeInstanceId!,
            dataPreviewSourceLogicalTableId!);
    }

    private void NotifyDataPreviewRowsChanged()
    {
        OnPropertyChanged(nameof(HasDataPreviewColumns));
        OnPropertyChanged(nameof(HasDataPreviewRows));
    }

    private void NotifyDataPreviewWorkbenchRowsChanged()
    {
        OnPropertyChanged(nameof(HasDataPreviewWorkbenchColumns));
        OnPropertyChanged(nameof(HasDataPreviewWorkbenchRows));
        OnPropertyChanged(nameof(DataPreviewWorkbenchPageText));
        CopyDataPreviewWorkbenchTsvCommand.NotifyCanExecuteChanged();
    }

    private void NotifyDataPreviewWorkbenchPagingChanged()
    {
        OnPropertyChanged(nameof(DataPreviewWorkbenchPageText));
        LoadPreviousDataPreviewWorkbenchPageCommand.NotifyCanExecuteChanged();
        LoadNextDataPreviewWorkbenchPageCommand.NotifyCanExecuteChanged();
    }

    private void NotifyDataPreviewWorkbenchDirtyStateChanged()
    {
        OnPropertyChanged(nameof(IsDataPreviewWorkbenchDirty));
        OnPropertyChanged(nameof(DataPreviewWorkbenchDirtyStateText));
        OnPropertyChanged(nameof(CanSaveDataPreviewWorkbenchAsDraft));
        OnPropertyChanged(nameof(DataPreviewWorkbenchSavePolicyText));
        RestoreDataPreviewWorkbenchDraftCommand.NotifyCanExecuteChanged();
        SaveDataPreviewWorkbenchAsCommand.NotifyCanExecuteChanged();
    }

    private static string FormatDataPreviewCell(JsonElement row, string column)
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

    partial void OnIsLoadingDataPreviewWorkbenchChanged(bool value)
    {
        OnPropertyChanged(nameof(IsDataPreviewWorkbenchBusy));
        LoadSelectedDataPreviewTableCommand.NotifyCanExecuteChanged();
        LoadPreviousDataPreviewWorkbenchPageCommand.NotifyCanExecuteChanged();
        LoadNextDataPreviewWorkbenchPageCommand.NotifyCanExecuteChanged();
        ParseDataPreviewWorkbenchPasteCommand.NotifyCanExecuteChanged();
        RestoreDataPreviewWorkbenchDraftCommand.NotifyCanExecuteChanged();
        SaveDataPreviewWorkbenchAsCommand.NotifyCanExecuteChanged();
        ShowDataPreviewDetailsCommand.NotifyCanExecuteChanged();
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

    partial void OnDataPreviewWorkbenchSearchTextChanged(string value)
    {
        DataPreviewWorkbenchClipboardText = string.Empty;
        ApplyDataPreviewWorkbenchSearch();
        UpdateDataPreviewWorkbenchLoadedMessage();
    }

    partial void OnDataPreviewWorkbenchClipboardTextChanged(string value)
    {
        OnPropertyChanged(nameof(HasDataPreviewWorkbenchClipboardText));
    }

    partial void OnDataPreviewWorkbenchPasteTextChanged(string value)
    {
        OnPropertyChanged(nameof(HasDataPreviewWorkbenchPasteText));
        ParseDataPreviewWorkbenchPasteCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsDataPreviewWorkbenchDraftChanged(bool value)
    {
        OnPropertyChanged(nameof(DataPreviewWorkbenchSourceText));
    }

    partial void OnSelectedDataPreviewStateChanged(DataPreviewStateListItemViewModel? value)
    {
        var previousTableRefId = SelectedDataPreviewTableOption?.TableRefId;
        DataPreviewTableOptions.Clear();
        if (value is not null)
        {
            foreach (var tableRef in value.TableRefs)
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
        LoadSelectedDataPreviewTableCommand.NotifyCanExecuteChanged();
    }

    partial void OnLoadedDataPreviewTableRefChanged(TableRefListItemViewModel? value)
    {
        OnPropertyChanged(nameof(DataPreviewWorkbenchSourceText));
        OnPropertyChanged(nameof(CanSaveDataPreviewWorkbenchAsDraft));
        OnPropertyChanged(nameof(DataPreviewWorkbenchSavePolicyText));
        LoadPreviousDataPreviewWorkbenchPageCommand.NotifyCanExecuteChanged();
        LoadNextDataPreviewWorkbenchPageCommand.NotifyCanExecuteChanged();
        SaveDataPreviewWorkbenchAsCommand.NotifyCanExecuteChanged();
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
