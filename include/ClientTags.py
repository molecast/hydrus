import ClientConstants as CC
import HydrusGlobals as HG
import HydrusSerialisable
import HydrusTags
import threading

def ConvertTagSliceToString( tag_slice ):
    
    if tag_slice == '':
        
        return 'unnamespaced tags'
        
    elif tag_slice == ':':
        
        return 'namespaced tags'
        
    elif tag_slice.count( ':' ) == 1 and tag_slice.endswith( ':' ):
        
        namespace = tag_slice[ : -1 ]
        
        return '\'' + namespace + '\' tags'
        
    else:
        
        return tag_slice
        
    
def RenderNamespaceForUser( namespace ):
    
    if namespace == '' or namespace is None:
        
        return 'unnamespaced'
        
    else:
        
        return namespace
        
    
def RenderTag( tag, render_for_user ):
    
    ( namespace, subtag ) = HydrusTags.SplitTag( tag )
    
    if namespace == '':
        
        return subtag
        
    else:
        
        if render_for_user:
            
            new_options = HG.client_controller.new_options
            
            if new_options.GetBoolean( 'show_namespaces' ):
                
                connector = new_options.GetString( 'namespace_connector' )
                
            else:
                
                return subtag
                
            
        else:
            
            connector = ':'
            
        
        return namespace + connector + subtag
        
    
def SortTagsList( tags, sort_type ):
    
    if sort_type in ( CC.SORT_BY_LEXICOGRAPHIC_DESC, CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_DESC ):
        
        reverse = True
        
    else:
        
        reverse = False
        
    
    if sort_type in ( CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_ASC, CC.SORT_BY_LEXICOGRAPHIC_NAMESPACE_DESC ):
        
        def key( tag ):
            
            # '{' is above 'z' in ascii, so this works for most situations
            
            ( namespace, subtag ) = HydrusTags.SplitTag( tag )
            
            if namespace == '':
                
                return ( '{', subtag )
                
            else:
                
                return ( namespace, subtag )
                
            
        
    else:
        
        key = None
        
    
    tags.sort( key = key, reverse = reverse )
    
class TagFilter( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_FILTER
    SERIALISABLE_NAME = 'Tag Filter Rules'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._lock = threading.Lock()
        
        self._tag_slices_to_rules = {}
        
    
    def __eq__( self, other ):
        
        return self._tag_slices_to_rules == other._tag_slices_to_rules
        
    
    def _GetTagSlices( self, tag ):
        
        ( namespace, subtag ) = HydrusTags.SplitTag( tag )
        
        tag_slices = []
        
        tag_slices.append( tag )
        
        if namespace != '':
            
            tag_slices.append( namespace + ':' )
            tag_slices.append( ':' )
            
        else:
            
            tag_slices.append( '' )
            
        
        return tag_slices
        
    
    def _GetSerialisableInfo( self ):
        
        return self._tag_slices_to_rules.items()
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        self._tag_slices_to_rules = dict( serialisable_info )
        
    
    def _TagOK( self, tag ):
        
        tag_slices = self._GetTagSlices( tag )
        
        blacklist_encountered = False
        
        for tag_slice in tag_slices:
            
            if tag_slice in self._tag_slices_to_rules:
                
                rule = self._tag_slices_to_rules[ tag_slice ]
                
                if rule == CC.FILTER_WHITELIST:
                    
                    return True # there is an exception for this class of tag
                    
                elif rule == CC.FILTER_BLACKLIST: # there is a rule against this class of tag
                    
                    blacklist_encountered = True
                    
                
            
        
        if blacklist_encountered: # rule against and no exceptions
            
            return False
            
        else:
            
            return True # no rules against or explicitly for, so permitted
            
        
    
    def Filter( self, tags ):
        
        with self._lock:
            
            return { tag for tag in tags if self._TagOK( tag ) }
            
        
    
    def GetTagSlicesToRules( self ):
        
        with self._lock:
            
            return dict( self._tag_slices_to_rules )
            
        
    
    def SetRule( self, tag_slice, rule ):
        
        with self._lock:
            
            self._tag_slices_to_rules[ tag_slice ] = rule
            
        
    
    def ToBlacklistString( self ):
        
        blacklist = []
        whitelist = []
        
        for ( tag_slice, rule ) in self._tag_slices_to_rules.items():
            
            if rule == CC.FILTER_BLACKLIST:
                
                blacklist.append( tag_slice )
                
            elif rule == CC.FILTER_WHITELIST:
                
                whitelist.append( tag_slice )
                
            
        
        blacklist.sort()
        whitelist.sort()
        
        if len( blacklist ) == 0:
            
            return 'no blacklist set'
            
        else:
            
            if set( blacklist ) == { '', ':' }:
                
                text = 'blacklisting on any tags'
                
            else:
                
                text = 'blacklisting on ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in blacklist ) )
                
            
            if len( whitelist ) > 0:
                
                text += ' except ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                
            
            return text
            
        
    
    def ToCensoredString( self ):
        
        blacklist = []
        whitelist = []
        
        for ( tag_slice, rule ) in self._tag_slices_to_rules.items():
            
            if rule == CC.FILTER_BLACKLIST:
                
                blacklist.append( tag_slice )
                
            elif rule == CC.FILTER_WHITELIST:
                
                whitelist.append( tag_slice )
                
            
        
        blacklist.sort()
        whitelist.sort()
        
        if len( blacklist ) == 0:
            
            return 'all tags allowed'
            
        else:
            
            if set( blacklist ) == { '', ':' }:
                
                text = 'no tags allowed'
                
            else:
                
                text = 'all but ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in blacklist ) ) + ' allowed'
                
            
            if len( whitelist ) > 0:
                
                text += ' except ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                
            
            return text
            
        
    
    def ToPermittedString( self ):
        
        blacklist = []
        whitelist = []
        
        for ( tag_slice, rule ) in self._tag_slices_to_rules.items():
            
            if rule == CC.FILTER_BLACKLIST:
                
                blacklist.append( tag_slice )
                
            elif rule == CC.FILTER_WHITELIST:
                
                whitelist.append( tag_slice )
                
            
        
        blacklist.sort()
        whitelist.sort()
        
        if len( blacklist ) == 0:
            
            return 'all tags'
            
        else:
            
            if set( blacklist ) == { '', ':' }:
                
                if len( whitelist ) == 0:
                    
                    text = 'no tags'
                    
                else:
                    
                    text = 'only ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                    
                
            elif set( blacklist ) == { '' }:
                
                text = 'all namespaced tags'
                
                if len( whitelist ) > 0:
                    
                    text += ' and ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                    
                
            elif set( blacklist ) == { ':' }:
                
                text = 'all unnamespaced tags'
                
                if len( whitelist ) > 0:
                    
                    text += ' and ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) )
                    
                
            else:
                
                text = 'all tags except ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in blacklist ) )
                
                if len( whitelist ) > 0:
                    
                    text += ' (except ' + ', '.join( ( ConvertTagSliceToString( tag_slice ) for tag_slice in whitelist ) ) + ')'
                    
                
            
        
        return text
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_FILTER ] = TagFilter
