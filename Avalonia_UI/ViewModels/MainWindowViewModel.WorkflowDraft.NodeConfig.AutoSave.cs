using System;
using System.ComponentModel;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private readonly Func<CancellationToken, Task> _nodeConfigAutoSaveDelay;
    private CancellationTokenSource? nodeConfigAutoSaveCancellation;
    private int nodeConfigAutoSaveRevision;
    private bool hasUnappliedNodeConfigChanges;
    private bool hasUnappliedSpecializedNodeConfigChanges;
    private bool isApplyingSelectedNodeConfigDraft;
    private bool preserveSelectedNodeConfigEditorForDraftChange;

    [ObservableProperty]
    private bool isNodeConfigAutoSaveEnabled = true;

    public string NodeConfigAutoSaveText => T("definition.node_config_auto_save");

    [RelayCommand]
    private void ToggleNodeConfigAutoSave()
    {
        if (IsNodeConfigAutoSaveEnabled)
        {
            FlushPendingNodeConfigAutoSave();
            IsNodeConfigAutoSaveEnabled = false;
            return;
        }

        IsNodeConfigAutoSaveEnabled = true;
        if (hasUnappliedNodeConfigChanges)
        {
            ScheduleNodeConfigAutoSave();
        }
    }

    private void OnSelectedNodeConfigFieldPropertyChanged(
        object? sender,
        PropertyChangedEventArgs args)
    {
        if (isApplyingSelectedNodeConfigDraft
            || sender is not NodeConfigEditableFieldInputViewModel field
            || args.PropertyName != nameof(NodeConfigEditableFieldInputViewModel.IsDirty))
        {
            return;
        }

        if (field.IsDirty)
        {
            MarkNodeConfigChanged(specialized: false);
        }
        else if (!hasUnappliedSpecializedNodeConfigChanges
            && SelectedNodeConfigEditableInputFields.All(item => !item.IsDirty))
        {
            hasUnappliedNodeConfigChanges = false;
            CancelPendingNodeConfigAutoSave();
        }
    }

    private void OnSelectedNodeSpecializedEditorConfigChanged(
        object? sender,
        EventArgs args)
    {
        MarkNodeConfigChanged(specialized: true);
    }

    private void MarkNodeConfigChanged(bool specialized)
    {
        if (isApplyingSelectedNodeConfigDraft)
        {
            return;
        }

        hasUnappliedNodeConfigChanges = true;
        hasUnappliedSpecializedNodeConfigChanges |= specialized;
        if (IsNodeConfigAutoSaveEnabled)
        {
            ScheduleNodeConfigAutoSave();
        }
    }

    private void ScheduleNodeConfigAutoSave()
    {
        CancelPendingNodeConfigAutoSave();
        if (!IsNodeConfigAutoSaveEnabled || !hasUnappliedNodeConfigChanges)
        {
            return;
        }

        var request = CancellationTokenSource.CreateLinkedTokenSource(_shutdown.Token);
        nodeConfigAutoSaveCancellation = request;
        var revision = ++nodeConfigAutoSaveRevision;
        _ = ApplyNodeConfigAfterAutoSaveDelayAsync(request, revision);
    }

    private async Task ApplyNodeConfigAfterAutoSaveDelayAsync(
        CancellationTokenSource request,
        int revision)
    {
        try
        {
            await _nodeConfigAutoSaveDelay(request.Token);
            if (request.IsCancellationRequested
                || revision != nodeConfigAutoSaveRevision
                || !IsNodeConfigAutoSaveEnabled
                || !hasUnappliedNodeConfigChanges)
            {
                return;
            }

            TryApplySelectedNodeConfigDraft(automatic: true);
        }
        catch (OperationCanceledException) when (request.IsCancellationRequested)
        {
        }
        finally
        {
            if (ReferenceEquals(nodeConfigAutoSaveCancellation, request))
            {
                nodeConfigAutoSaveCancellation = null;
            }

            request.Dispose();
        }
    }

    private bool FlushPendingNodeConfigAutoSave()
    {
        if (isApplyingSelectedNodeConfigDraft)
        {
            return true;
        }

        CancelPendingNodeConfigAutoSave();
        if (IsNodeConfigAutoSaveEnabled && hasUnappliedNodeConfigChanges)
        {
            return TryApplySelectedNodeConfigDraft(automatic: true);
        }

        return true;
    }

    private void CancelPendingNodeConfigAutoSave()
    {
        nodeConfigAutoSaveRevision++;
        var cancellation = nodeConfigAutoSaveCancellation;
        nodeConfigAutoSaveCancellation = null;
        cancellation?.Cancel();
        cancellation?.Dispose();
    }

    partial void OnIsNodeConfigAutoSaveEnabledChanged(bool value)
    {
        OnPropertyChanged(nameof(NodeConfigAutoSaveText));
    }
}
