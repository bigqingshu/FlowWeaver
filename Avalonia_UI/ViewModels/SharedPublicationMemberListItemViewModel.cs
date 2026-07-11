using System;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class SharedPublicationMemberListItemViewModel : ViewModelBase
{
    private readonly Func<SharedPublicationMemberListItemViewModel, Task>? _preview;
    private readonly Func<string, string> _translate;

    public SharedPublicationMemberListItemViewModel(
        SharedPublicationMemberDto member,
        Func<SharedPublicationMemberListItemViewModel, Task>? preview = null,
        Func<string, string>? translate = null)
    {
        _preview = preview;
        _translate = translate ?? (key => key);
        ExportName = member.ExportName;
        TableRefId = member.TableRefId;
        ExactTableVersion = member.ExactTableVersion;
        TableRefLifecycleStatus = member.TableRefLifecycleStatus;
        TableRefStorageKind = member.TableRefStorageKind;
        LogicalTableId = member.LogicalTableId;
        CanReadRows = member.CanReadRows;
    }

    public string ExportName { get; }

    public string TableRefId { get; }

    public int ExactTableVersion { get; }

    public string TableRefLifecycleStatus { get; }

    public string TableRefStorageKind { get; }

    public string LogicalTableId { get; }

    public bool CanReadRows { get; }

    public bool CanPreview => _preview is not null && CanReadRows;

    public string VersionText => $"v{ExactTableVersion}";

    public string LifecycleStatusText => string.IsNullOrWhiteSpace(TableRefLifecycleStatus)
        ? "-"
        : TableRefLifecycleStatus;

    public string PreviewText => _translate("data.shared_member.preview");

    public string AvailabilityText => CanReadRows
        ? _translate("data.shared_member.available")
        : TableRefLifecycleStatus switch
        {
            "RELEASED" => _translate("data.shared_member.released"),
            "RETIRED" => _translate("data.shared_member.retired"),
            "ORPHANED" => _translate("data.shared_member.orphaned"),
            _ => _translate("data.shared_member.unavailable"),
        };

    private bool CanPreviewMember()
    {
        return CanPreview;
    }

    [RelayCommand(CanExecute = nameof(CanPreviewMember))]
    private Task PreviewAsync()
    {
        return _preview?.Invoke(this) ?? Task.CompletedTask;
    }
}
