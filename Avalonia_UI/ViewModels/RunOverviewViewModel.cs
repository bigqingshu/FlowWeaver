using System;
using System.Globalization;
using System.Linq;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public sealed partial class RunOverviewViewModel : ViewModelBase
{
    private static readonly JsonSerializerOptions DisplayJsonOptions = new(FlowWeaverJson.Options)
    {
        WriteIndented = true,
    };

    private readonly IRunReviewService runReviewService;
    private readonly Func<string, string> translate;
    private readonly DisplayTextFormatter displayTextFormatter;

    private EngineHostConnectionSettings? settings;
    private string? workflowRunId;
    private bool canUseActions;
    private bool isActive;
    private CancellationTokenSource? loadCancellation;
    private int requestVersion;
    private Task pendingLoadTask = Task.CompletedTask;

    public event Action<RunMonitorDrilldownRequest>? DrilldownRequested;

    public RunOverviewViewModel(
        IRunReviewService runReviewService,
        Func<string, string> translate,
        DisplayTextFormatter? displayTextFormatter = null)
    {
        this.runReviewService = runReviewService;
        this.translate = translate;
        this.displayTextFormatter = displayTextFormatter ?? DisplayTextFormatter.Invariant;
        Message = SelectRunText;
    }

    [ObservableProperty]
    private RunReviewDto? review;

    [ObservableProperty]
    private bool isLoading;

    [ObservableProperty]
    private bool hasLoaded;

    [ObservableProperty]
    private string message;

    [ObservableProperty]
    private string? errorMessage;

    public string SectionText => translate("runs.overview.section");

    public string RefreshText => translate("common.refresh");

    public string SelectRunText => translate("runs.overview.select_run");

    public string ActivateText => translate("runs.overview.activate");

    public string BasicText => translate("runs.overview.basic");

    public string TableSummaryText => translate("runs.overview.table_summary");

    public string AdvancedText => translate("runs.overview.advanced");

    public string StorageKindsLabel => translate("runs.overview.storage_kinds");

    public string LifecycleStatusesLabel => translate("runs.overview.lifecycle_statuses");

    public string PreviewLabel => translate("runs.overview.preview");

    public string RunErrorText => translate("runs.overview.run_error");

    public string ViewTablesText => translate("runs.drilldown.tables");

    public string ViewPreviewText => translate("runs.drilldown.preview");

    public string ViewLogsText => translate("runs.drilldown.logs");

    public string RunIdLabel => translate("runs.overview.run_id");

    public string WorkflowLabel => translate("runs.overview.workflow");

    public string RevisionLabel => translate("runs.overview.revision");

    public string StatusLabel => translate("runs.overview.status");

    public string ModeLabel => translate("runs.overview.mode");

    public string TriggerLabel => translate("runs.overview.trigger");

    public string TargetLabel => translate("runs.overview.target");

    public string StartedLabel => translate("runs.overview.started");

    public string FinishedLabel => translate("runs.overview.finished");

    public string DurationLabel => translate("runs.overview.duration");

    public string CompletionReasonLabel => translate("runs.overview.completion_reason");

    public string RunIdText => Review?.Run.WorkflowRunId ?? string.Empty;

    public string WorkflowText => Review is null
        ? string.Empty
        : $"{Review.Run.WorkflowId} v{Review.Run.WorkflowVersion}";

    public string RevisionText => ValueOrDash(Review?.Run.RevisionId);

    public string StatusText => Review is null
        ? string.Empty
        : displayTextFormatter.FormatRuntimeStatus(Review.Run.Status);

    public string ModeText => FormatProtocolValue("runs.mode", Review?.Run.RunMode);

    public string TriggerText => FormatProtocolValue("runs.trigger", Review?.Run.TriggerSource);

    public string TargetText => ValueOrDash(Review?.Run.TargetNodeInstanceId);

    public string StartedText => FormatDateTime(Review?.Run.StartedAt);

    public string FinishedText => FormatDateTime(Review?.Run.FinishedAt);

    public string DurationText => FormatDuration(Review?.Run.StartedAt, Review?.Run.FinishedAt);

    public string CompletionReasonText => ValueOrDash(Review?.Run.CompletionReason);

    public string CountsText => Review is null
        ? string.Empty
        : string.Format(
            CultureInfo.CurrentCulture,
            translate("runs.overview.counts_format"),
            Review.NodeRuns.Length,
            Review.TableRefSummary.Total,
            Review.TableRefSummary.Readable);

    public string StorageKindsText => Review is null
        ? string.Empty
        : FormatCounts(Review.TableRefSummary.ByStorageKind);

    public string LifecycleStatusesText => Review is null
        ? string.Empty
        : FormatCounts(Review.TableRefSummary.ByLifecycleStatus);

    public string PreviewText => Review is null
        ? string.Empty
        : string.Format(
            CultureInfo.CurrentCulture,
            translate("runs.overview.preview_format"),
            FormatBoolean(Review.DataPreview.UsesPagedRows),
            FormatBoolean(Review.DataPreview.RowDataEmbedded),
            Review.DataPreview.ReadableTableRefIds.Length);

    public string DiagnosticText => Review is null
        ? string.Empty
        : string.Join(
            Environment.NewLine,
            $"{translate("runs.overview.definition_hash")}: {ValueOrDash(Review.Run.DefinitionHash)}",
            $"{translate("runs.overview.owner_process")}: {ValueOrDash(Review.Run.OwnerProcessId)}",
            $"{translate("runs.overview.process_generation")}: {Review.Run.ProcessGeneration}",
            $"{translate("runs.overview.fencing_token")}: {ValueOrDash(Review.Run.FencingToken)}",
            $"{translate("runs.overview.input_snapshot")}: {ValueOrDash(Review.Run.InputSnapshotId)}",
            $"{translate("runs.overview.state_version")}: {Review.Run.StateVersion}");

    public string RunErrorJson => FormatJson(Review?.Run.Error);

    public bool HasReview => Review is not null;

    public bool HasError => !string.IsNullOrWhiteSpace(ErrorMessage);

    public bool HasRunError => !string.IsNullOrWhiteSpace(RunErrorJson);

    public Task WaitForPendingLoadAsync()
    {
        return pendingLoadTask;
    }

    public void SetContext(
        EngineHostConnectionSettings connectionSettings,
        string? selectedWorkflowRunId,
        bool actionsEnabled)
    {
        var normalizedRunId = string.IsNullOrWhiteSpace(selectedWorkflowRunId)
            ? null
            : selectedWorkflowRunId.Trim();
        var contextChanged = settings is null
            || !string.Equals(settings.BaseUrl, connectionSettings.BaseUrl, StringComparison.Ordinal)
            || !string.Equals(settings.Token, connectionSettings.Token, StringComparison.Ordinal)
            || !string.Equals(workflowRunId, normalizedRunId, StringComparison.Ordinal);

        settings = connectionSettings;
        workflowRunId = normalizedRunId;
        canUseActions = actionsEnabled;
        RefreshCommand.NotifyCanExecuteChanged();
        NotifyDrilldownCommandStateChanged();

        if (!contextChanged)
        {
            if (!canUseActions)
            {
                CancelRequest();
            }
            else if (isActive && !HasLoaded && !IsLoading)
            {
                BeginLoad();
            }

            return;
        }

        CancelRequest();
        Review = null;
        HasLoaded = false;
        ErrorMessage = null;
        Message = workflowRunId is null
            ? SelectRunText
            : isActive ? translate("runs.overview.ready") : ActivateText;

        if (isActive && canUseActions && workflowRunId is not null)
        {
            BeginLoad();
        }
    }

    public void SetActive(bool active)
    {
        if (isActive == active)
        {
            return;
        }

        isActive = active;
        if (!active)
        {
            if (IsLoading)
            {
                CancelRequest();
                Message = ActivateText;
            }

            return;
        }

        if (!HasLoaded && canUseActions && workflowRunId is not null)
        {
            BeginLoad();
        }
    }

    public void RefreshLocalizedText()
    {
        OnPropertyChanged(nameof(SectionText));
        OnPropertyChanged(nameof(RefreshText));
        OnPropertyChanged(nameof(SelectRunText));
        OnPropertyChanged(nameof(ActivateText));
        OnPropertyChanged(nameof(BasicText));
        OnPropertyChanged(nameof(TableSummaryText));
        OnPropertyChanged(nameof(AdvancedText));
        OnPropertyChanged(nameof(StorageKindsLabel));
        OnPropertyChanged(nameof(LifecycleStatusesLabel));
        OnPropertyChanged(nameof(PreviewLabel));
        OnPropertyChanged(nameof(RunErrorText));
        OnPropertyChanged(nameof(ViewTablesText));
        OnPropertyChanged(nameof(ViewPreviewText));
        OnPropertyChanged(nameof(ViewLogsText));
        RaiseReviewPropertyChanges();

        if (workflowRunId is null)
        {
            Message = SelectRunText;
        }
        else if (!isActive && !HasLoaded)
        {
            Message = ActivateText;
        }
        else if (IsLoading)
        {
            Message = translate("runs.overview.loading");
        }
        else if (HasLoaded && Review is not null)
        {
            Message = translate("runs.overview.loaded");
        }
    }

    [RelayCommand(CanExecute = nameof(CanRefresh))]
    private async Task RefreshAsync()
    {
        BeginLoad();
        await pendingLoadTask;
    }

    [RelayCommand(CanExecute = nameof(CanDrilldown))]
    private void ViewTables()
    {
        RequestDrilldown(RunMonitorDrilldownDestination.Tables);
    }

    [RelayCommand(CanExecute = nameof(CanDrilldown))]
    private void ViewPreview()
    {
        RequestDrilldown(RunMonitorDrilldownDestination.Preview);
    }

    [RelayCommand(CanExecute = nameof(CanDrilldown))]
    private void ViewLogs()
    {
        RequestDrilldown(RunMonitorDrilldownDestination.Logs);
    }

    private bool CanRefresh()
    {
        return isActive
            && canUseActions
            && !IsLoading
            && !string.IsNullOrWhiteSpace(workflowRunId);
    }

    private bool CanDrilldown()
    {
        return canUseActions && !string.IsNullOrWhiteSpace(workflowRunId);
    }

    private void RequestDrilldown(RunMonitorDrilldownDestination destination)
    {
        if (workflowRunId is not null)
        {
            DrilldownRequested?.Invoke(new RunMonitorDrilldownRequest(
                destination,
                workflowRunId));
        }
    }

    private void NotifyDrilldownCommandStateChanged()
    {
        ViewTablesCommand.NotifyCanExecuteChanged();
        ViewPreviewCommand.NotifyCanExecuteChanged();
        ViewLogsCommand.NotifyCanExecuteChanged();
    }

    private void BeginLoad()
    {
        if (!CanRefresh() || settings is null || workflowRunId is null)
        {
            return;
        }

        CancelRequest();
        loadCancellation = new CancellationTokenSource();
        var version = ++requestVersion;
        var requestedRunId = workflowRunId;
        pendingLoadTask = LoadAsync(
            settings,
            requestedRunId,
            version,
            loadCancellation.Token);
    }

    private async Task LoadAsync(
        EngineHostConnectionSettings requestedSettings,
        string requestedRunId,
        int version,
        CancellationToken cancellationToken)
    {
        IsLoading = true;
        ErrorMessage = null;
        Message = translate("runs.overview.loading");
        try
        {
            var response = await runReviewService.GetAsync(
                requestedSettings,
                requestedRunId,
                cancellationToken);
            if (IsStale(version, requestedRunId))
            {
                return;
            }

            HasLoaded = true;
            if (!response.Ok || response.Data is null)
            {
                Review = null;
                ErrorMessage = FormatError(response.Error?.ErrorCode, response.Error?.Message);
                Message = translate("runs.overview.load_failed");
                return;
            }

            Review = response.Data;
            Message = translate("runs.overview.loaded");
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
        catch (Exception exception)
        {
            if (!IsStale(version, requestedRunId))
            {
                HasLoaded = true;
                Review = null;
                ErrorMessage = exception.Message;
                Message = translate("runs.overview.load_failed");
            }
        }
        finally
        {
            if (!IsStale(version, requestedRunId))
            {
                IsLoading = false;
            }
        }
    }

    private bool IsStale(int version, string requestedRunId)
    {
        return version != requestVersion
            || !string.Equals(requestedRunId, workflowRunId, StringComparison.Ordinal);
    }

    private void CancelRequest()
    {
        requestVersion++;
        loadCancellation?.Cancel();
        loadCancellation?.Dispose();
        loadCancellation = null;
        IsLoading = false;
    }

    partial void OnReviewChanged(RunReviewDto? value)
    {
        RaiseReviewPropertyChanges();
    }

    partial void OnIsLoadingChanged(bool value)
    {
        RefreshCommand.NotifyCanExecuteChanged();
    }

    partial void OnErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasError));
    }

    private void RaiseReviewPropertyChanges()
    {
        OnPropertyChanged(nameof(HasReview));
        OnPropertyChanged(nameof(RunIdLabel));
        OnPropertyChanged(nameof(WorkflowLabel));
        OnPropertyChanged(nameof(RevisionLabel));
        OnPropertyChanged(nameof(StatusLabel));
        OnPropertyChanged(nameof(ModeLabel));
        OnPropertyChanged(nameof(TriggerLabel));
        OnPropertyChanged(nameof(TargetLabel));
        OnPropertyChanged(nameof(StartedLabel));
        OnPropertyChanged(nameof(FinishedLabel));
        OnPropertyChanged(nameof(DurationLabel));
        OnPropertyChanged(nameof(CompletionReasonLabel));
        OnPropertyChanged(nameof(RunIdText));
        OnPropertyChanged(nameof(WorkflowText));
        OnPropertyChanged(nameof(RevisionText));
        OnPropertyChanged(nameof(StatusText));
        OnPropertyChanged(nameof(ModeText));
        OnPropertyChanged(nameof(TriggerText));
        OnPropertyChanged(nameof(TargetText));
        OnPropertyChanged(nameof(StartedText));
        OnPropertyChanged(nameof(FinishedText));
        OnPropertyChanged(nameof(DurationText));
        OnPropertyChanged(nameof(CompletionReasonText));
        OnPropertyChanged(nameof(CountsText));
        OnPropertyChanged(nameof(StorageKindsText));
        OnPropertyChanged(nameof(LifecycleStatusesText));
        OnPropertyChanged(nameof(PreviewText));
        OnPropertyChanged(nameof(DiagnosticText));
        OnPropertyChanged(nameof(RunErrorJson));
        OnPropertyChanged(nameof(HasRunError));
    }

    private string FormatProtocolValue(string prefix, string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return "-";
        }

        var key = $"{prefix}.{value}";
        var localized = translate(key);
        return string.Equals(localized, key, StringComparison.Ordinal) ? value : localized;
    }

    private string FormatBoolean(bool value)
    {
        return translate(value ? "common.on" : "common.off");
    }

    private static string FormatCounts(System.Collections.Generic.IReadOnlyDictionary<string, int> counts)
    {
        return counts.Count == 0
            ? "-"
            : string.Join(
                ", ",
                counts
                    .OrderBy(item => item.Key, StringComparer.Ordinal)
                    .Select(item => $"{item.Key}: {item.Value}"));
    }

    private static string FormatDateTime(DateTimeOffset? value)
    {
        return value?.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss zzz", CultureInfo.CurrentCulture)
            ?? "-";
    }

    private static string FormatDuration(DateTimeOffset? startedAt, DateTimeOffset? finishedAt)
    {
        if (startedAt is null)
        {
            return "-";
        }

        var duration = (finishedAt ?? DateTimeOffset.Now) - startedAt.Value;
        if (duration < TimeSpan.Zero)
        {
            return "-";
        }

        return duration.TotalHours >= 1
            ? duration.ToString(@"hh\:mm\:ss", CultureInfo.CurrentCulture)
            : duration.ToString(@"mm\:ss", CultureInfo.CurrentCulture);
    }

    private static string FormatJson(JsonElement? value)
    {
        return value is null
            || value.Value.ValueKind is JsonValueKind.Null or JsonValueKind.Undefined
            ? string.Empty
            : JsonSerializer.Serialize(value.Value, DisplayJsonOptions);
    }

    private static string ValueOrDash(string? value)
    {
        return string.IsNullOrWhiteSpace(value) ? "-" : value;
    }

    private static string FormatError(string? errorCode, string? errorMessage)
    {
        if (string.IsNullOrWhiteSpace(errorCode))
        {
            return errorMessage ?? string.Empty;
        }

        return string.IsNullOrWhiteSpace(errorMessage)
            ? errorCode
            : $"{errorCode}: {errorMessage}";
    }
}
