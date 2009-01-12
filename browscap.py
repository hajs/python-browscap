import os
import re
import urllib
import urllib.request

from configparser import *

class UserAgentParser:
	"""
	This class uses browscap.ini from http://browsers.garykeith.com/ to parse user-agent header strings and 
        provide info such as browser family, OS, version, etc.
	"""	

	DEBUG = False

	def __init__(self, ):
		self.user_agent_properties = {}    # Maps section names to properties of user agents. Contains only non-parent sections.
		self.user_agent_regexps = {}       # Maps section names to compiled python regexps that match user agent strings corresponding to the section name. Contains only non-parent sections.
		self.__match_cache = {}

	def load(self, browscap_ini_filepath="browscap.ini"):
		"""
		Loads and parses the browscap.ini file.		

		Keyword Args:
		- browscap_ini_filepath - path of the browscap.ini file. 
		"""
		if not os.path.isfile(browscap_ini_filepath):
			raise Exception("File not found: " + str(browscap_ini_filepath))

		cp = ConfigParser()
		cp.readfp(open(browscap_ini_filepath, "r", encoding="latin-1"))

		# Remove meta sections
		cp.remove_section("*")
		cp.remove_section("GJK_Browscap_Version")
		
		# Create a list of non-parent sections
		child_sections = set(cp.sections())
		for section in cp.sections():			
			# Remove this section's parent from the list
			if cp.has_option(section, "parent"):
				parent = cp.get(section, "parent") 
				if parent in child_sections:
					child_sections.remove(parent)
		
		# Populate user_agent_properties and user_agent_regexps 
		for section in child_sections:
			# Get user agent properties for this section
			try:
				properties = self.__get_browser_props(cp, section, safe=False)			
			except Exception as e:
				print("Failed to parse data for [%s] - ERROR: %s" % (section, str(e)) )
				continue
				
			self.user_agent_properties[section] = properties
			
			# Convert .ini file regexp syntax into python regexp syntax
			user_agent_re = section
			for unsafe_char in list("^$()[].-"):
				user_agent_re = user_agent_re.replace(unsafe_char, "\%s" % unsafe_char)

			user_agent_re = user_agent_re.replace("?", ".").replace("*", ".*?")
			user_agent_re = "^%s$" % user_agent_re
			
			#print(section, user_agent_re)
			user_agent_re = re.compile(user_agent_re)
			
			self.user_agent_regexps[section] = user_agent_re

		if UserAgentParser.DEBUG:
			print("Finished parsing %d sections, %d non-parent sections" % (len(cp.sections()), len(child_sections)))


	
	def load_from_url(self, browscap_ini_url="http://browsers.garykeith.com/stream.asp?BrowsCapINI", save_to_filepath="browscap.ini", proxy=""):
		"""
		Loads and parses the browscap.ini file from the web. Default url can be changed via constructor.

		Keyword Args:
		- browscap_ini_url - where to get the browscap.ini file. 
		- proxy - proxy to use when retrieving browscap_ini_url (Example: http://www.example.com:3128/)
		"""
		
		if proxy:
			proxy_handler = urllib.request.ProxyHandler({'http': proxy})
			request_builder = urllib.request.build_opener(proxy_handler)
			c = request_builder.open(browscap_ini_url)
			
		else :
			c = urllib.request.urlopen(browscap_ini_url)
		contents = c.read()
		c.close()	

		file = open(save_to_filepath, "wb+")
		file.write(contents)
		file.close()

		self.load(save_to_filepath)
		
	def get_all_user_agents(self):
		"""Returns a list of all known user-agent strings"""
		self.__check_init()	
		
		return list(self.user_agent_properties.keys()) # Return a copy

	def query(self, user_agent_string, safe=False):
		"""
		Looks up the given user agent string and returns a dictionary containing information on this browser or bot.
		safe - if this is set to True, an Exception will not be thrown if the given user agent is unknown. The default value is False, so that an Exception is thrown.
		"""

		self.__check_init()
	
		# Try to match user_agent_string to section name		
		section = self.__match(user_agent_string)
		if not section:
			if safe:
				return {}
			else:
				raise Exception("Unknown user agent: [" + str(user_agent_string) + "]")

		# Recursively get browser properties
		return self.user_agent_properties[section]

	def __check_init(self):
		"""Checks whether load(..) has been called."""
		
		if not self.user_agent_regexps:
			raise Exception("Browser properties not initialized. Must call load(..) method first.")

	

	def __match(self, user_agent_string):		
		"""
		Looks through the leaf sections to find one that matches the given user_agent_string.
		Returns either the matching section name or "" if no match found.		
		"""
		
		if user_agent_string in self.__match_cache:
			return self.__match_cache[user_agent_string]		


		matching_section=""
		for section in self.user_agent_regexps.keys():
			# Find the longest regexp that matches the given user_agent_string. The length check is needed since multiple 	reg-exps may match the user_agent_string.
			if self.user_agent_regexps[section].match(user_agent_string) and len(section) > len(matching_section):
				matching_section = section
	
		
		self.__match_cache[user_agent_string] = matching_section
		return matching_section
		
		
	def __get_browser_props(self, cp, section, safe=False):		
		"""
		Recursively traverses the properties tree (based on 'parent' attribute of each section) and 
		returns a dictionary of all browser properties for the given section name. The properties lower 
		in the tree override those higher in the tree."""
		
		result = {}

		# Get parent properties	recursively	
		if cp.has_option(section, "parent"):
			parent = cp.get(section, "parent")
			parent_properties = self.__get_browser_props( cp, parent, safe ) 
			result.update(parent_properties) 
		
		# Overshadow any parent properties with properties specific to this user-agent.
		my_properties =	dict(cp.items(section))
		result.update(my_properties)

		return result


	

# Prints the properties for a single user agent string. 
def test(user_agent_string = ""):
	uap = UserAgentParser()
	uap.load_from_url(browscap_ini_url="http://browsers.garykeith.com/stream.asp?PHP_BrowsCapINI", proxy="")
	#uap.load_from_url(browscap_ini_url="http://browsers.garykeith.com/stream.asp?Lite_PHP_BrowsCapINI", proxy="")
	
	#uap.load()
	#print(uap.get_all_user_agents())
	if user_agent_string:
		print(uap.query(user_agent_string))
	else:
		for agent in ["Mozilla/5.0 (compatible; Konqueror/3.5; Linux; X11; de) KHTML/3.5.2 (like Gecko) Kubuntu 6.06 Dapper",
			"Mozilla/5.0 (X11; U; Linux i686; de; rv:1.8.0.5) Gecko/20060731 Ubuntu/dapper-security Firefox/1.5.0.5",
			"Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.7.12) Gecko/20060216 Debian/1.7.12-1.1ubuntu2",
			"Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.0.5) Gecko/20060731 Ubuntu/dapper-security Epiphany/2.14 Firefox/1.5.0.5",
			"Opera/9.00 (X11; Linux i686; U; en)",
			"Wget/1.10.2",
			"Mozilla/5.0 (X11; Linux i686; U;) Gecko/20051128 Kazehakase/0.3.3 Debian/0.3.3-1",
			"Mozilla/5.0 (X11; U; Linux i386) Gecko/20063102 Galeon/1.3test",
			"Mozilla/4.0 (compatible; MSIE 6.0; Windows 98)"]:
			results = uap.query(agent, safe=True)
			if ("browser" in results) and ("version" in results):
				print(agent, " is ", results["browser"], results["version"])
			else:
				print(agent, " is unknown")
		
# Validates the browscap.ini file by making sure all browsers have the 'platform', 'browser', 'version' properties defined.
def validate():
	a = UserAgentParser()
	a.load_from_url(proxy="")
	
	# Make sure all browsers have properties
	all_b = set()
	all_p = set()
	for b in a.get_all_user_agents():
		par = a.query(b, safe=True)
		#print(par)
		if not "platform" in par:
			print("No platform for %s" % b)
			continue

		if not "browser" in par:
			print("No browser for %s" % b)
			continue

		if not "version" in par:
			print("No version for %s" % b)
			continue		
		p = par["platform"]
		b = par["browser"]
		all_p.add(p)
		all_b.add(b)
		#print("p: %s, b: %s, v: %s" % (p, b, par["version"]))
	
	#print("\nAll browsers", all_b)
	print("\nAll platforms", all_p)


#test()
#validate()
