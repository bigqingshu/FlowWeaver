using System;
using Avalonia_UI.Api;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class SharedPublicationMemberOptionViewModel : ViewModelBase
{
    private readonly Action<SharedPublicationMemberOptionViewModel> _selectionChanged;

    public SharedPublicationMemberOptionViewModel(
        SharedPublicationMemberDto member,
        bool isSelected,
        Action<SharedPublicationMemberOptionViewModel> selectionChanged)
    {
        PublicationId = member.PublicationId;
        ExportName = member.ExportName;
        TableRefId = member.TableRefId;
        ExactTableVersion = member.ExactTableVersion;
        this.isSelected = isSelected;
        _selectionChanged = selectionChanged;
    }

    public string PublicationId { get; }

    public string ExportName { get; }

    public string TableRefId { get; }

    public int ExactTableVersion { get; }

    public string VersionText => $"v{ExactTableVersion}";

    [ObservableProperty]
    private bool isSelected;

    partial void OnIsSelectedChanged(bool value)
    {
        _selectionChanged(this);
    }
}
