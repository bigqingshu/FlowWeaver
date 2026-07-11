using System.Threading;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private const int SharedPublicationMemberPageSize = 100;

    private CancellationTokenSource? sharedPublicationMembersLoadCancellation;

    private int sharedPublicationMemberOffset;

    [ObservableProperty]
    private SharedPublicationMemberListItemViewModel?
        selectedSharedPublicationVersionMember;

    [ObservableProperty]
    private bool isLoadingSharedPublicationVersionMembers;

    [ObservableProperty]
    private bool hasMoreSharedPublicationVersionMembers;
}
